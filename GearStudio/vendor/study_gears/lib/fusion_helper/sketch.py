# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from ...guard import checkpoint
from collections.abc import Iterable
from typing import cast

import adsk.core, adsk.fusion

from .helpers import collection
from .vector import Vector
from .point3d import point3d


def sketch_fix_all(sketch: adsk.fusion.Sketch):
    """Fix all sketch contents."""
    for p in sketch.sketchPoints:
        checkpoint()
        p.isFixed = True
    for c in sketch.sketchCurves:
        checkpoint()
        c.isFixed = True
    for t in sketch.sketchTexts:
        checkpoint()
        t.isFixed = True


def sketch_line(
    sketch: adsk.fusion.Sketch,
    p1: Vector | adsk.core.Point3D | adsk.fusion.SketchPoint,
    p2: Vector | adsk.core.Point3D | adsk.fusion.SketchPoint,
):
    """Add a line by two points, accepting both Vector and Point3D types."""
    if isinstance(p1, Vector):
        p1 = point3d(p1)
    if isinstance(p2, Vector):
        p2 = point3d(p2)

    return sketch.sketchCurves.sketchLines.addByTwoPoints(p1, p2)  # type: ignore[arg-type]


def sketch_rectangle(
    sketch: adsk.fusion.Sketch,
    corner1: Vector | adsk.core.Point3D | adsk.fusion.SketchPoint,
    corner2: Vector | adsk.core.Point3D | adsk.fusion.SketchPoint,
    reference: adsk.fusion.SketchPoint | None = None,
    fillet: float | None = None,
    square: bool = False,
):
    """Add a rectangle defined by two corner points.
    Optionally, an reference point can be specified to constrain the rectangle's position.
    If a fillet radius is provided, fillets will be added to the corners.
    Returns a list of sketch curves created, including lines in the order
    of bottom, right, top and left, and fillets, if applicable, in the order
    of lower-left, lower-right, upper-right, and upper-lef.
    """

    p1 = corner1.geometry if isinstance(corner1, adsk.fusion.SketchPoint) else corner1
    p2 = corner2.geometry if isinstance(corner2, adsk.fusion.SketchPoint) else corner2
    l1 = sketch_line(sketch, corner1, Vector(p2.x, p1.y))
    sketch.geometricConstraints.addHorizontal(l1)
    l2 = sketch_line(sketch, l1.endSketchPoint, corner2)
    sketch.geometricConstraints.addVertical(l2)
    l3 = sketch_line(sketch, l2.endSketchPoint, Vector(p1.x, p2.y))
    sketch.geometricConstraints.addHorizontal(l3)
    l4 = sketch_line(sketch, l3.endSketchPoint, l1.startSketchPoint)
    sketch.geometricConstraints.addVertical(l4)
    sketch.sketchDimensions.addDistanceDimension(
        l1.startSketchPoint,
        l1.endSketchPoint,
        cast(
            adsk.fusion.DimensionOrientations,
            adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
        ),
        point3d((p1.x + p2.x) / 2, p1.y - 0.2),
    )
    if not square:
        sketch.sketchDimensions.addDistanceDimension(
            l4.startSketchPoint,
            l4.endSketchPoint,
            cast(
                adsk.fusion.DimensionOrientations,
                adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
            ),
            point3d(p1.x - 0.2, (p1.y + p2.y) / 2),
        )

    if fillet is not None and fillet > 0:
        f1 = sketch_fillet(sketch, l1, l4, fillet)
        f2 = sketch_fillet(sketch, l2, l1, fillet)
        f3 = sketch_fillet(sketch, l3, l2, fillet)
        f4 = sketch_fillet(sketch, l4, l3, fillet)
        sketch.sketchDimensions.addRadialDimension(
            f1, point3d(-2 * fillet, -2 * fillet, 0)
        )
        sketch.geometricConstraints.addEqual(f1, f2)
        sketch.geometricConstraints.addEqual(f2, f3)
        sketch.geometricConstraints.addEqual(f3, f4)

    if square:
        sketch.geometricConstraints.addEqual(l1, l4)

    if reference is not None:
        if (
            abs(reference.geometry.x - p1.x) < 0.0001
            and abs(reference.geometry.y - p1.y) < 0.0001
            and (fillet is None or fillet == 0)
        ):
            try:
                sketch.geometricConstraints.addCoincident(
                    l1.startSketchPoint, reference
                )
            except RuntimeError:
                # If the coincident constraint fails, we skip it
                pass
        else:
            if abs(reference.geometry.x - p1.x) < 0.0001:
                try:
                    sketch.geometricConstraints.addCoincident(
                        reference,
                        l4,
                    )
                except RuntimeError:
                    # If the coincident constraint fails, we skip it
                    pass
            else:
                sketch.sketchDimensions.addDistanceDimension(
                    reference,
                    l4.endSketchPoint,
                    cast(
                        adsk.fusion.DimensionOrientations,
                        adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
                    ),
                    point3d(
                        (reference.geometry.x + p1.x) / 2, reference.geometry.y - 0.2
                    ),
                )
            if abs(reference.geometry.y - p1.y) < 0.0001:
                try:
                    sketch.geometricConstraints.addCoincident(
                        reference,
                        l1,
                    )
                except RuntimeError:
                    # If the coincident constraint fails, we skip it
                    pass
            else:
                sketch.sketchDimensions.addDistanceDimension(
                    reference,
                    l1.startSketchPoint,
                    cast(
                        adsk.fusion.DimensionOrientations,
                        adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
                    ),
                    point3d(
                        reference.geometry.x - 0.2, (reference.geometry.y + p1.y) / 2
                    ),
                )

    if fillet is None or fillet <= 0:
        return [l1, l2, l3, l4]
    return [l1, l2, l3, l4, f1, f2, f3, f4]


def sketch_fillet(
    sketch: adsk.fusion.Sketch,
    line1: (
        adsk.fusion.SketchLine
        | adsk.fusion.SketchArc
        | adsk.fusion.SketchFittedSpline
        | adsk.fusion.SketchControlPointSpline
    ),
    line2: (
        adsk.fusion.SketchLine
        | adsk.fusion.SketchArc
        | adsk.fusion.SketchFittedSpline
        | adsk.fusion.SketchControlPointSpline
    ),
    radius: float,
    add_dimension: bool = False,
):
    """Add a fillet between two lines at specified points."""
    point1 = line1.startSketchPoint.geometry
    if point1.isEqualToByTolerance(line2.startSketchPoint.geometry, 0.0001):
        point2 = line2.startSketchPoint.geometry
    elif point1.isEqualToByTolerance(line2.endSketchPoint.geometry, 0.0001):
        point2 = line2.endSketchPoint.geometry
    else:
        point1 = line1.endSketchPoint.geometry
        if point1.isEqualToByTolerance(line2.startSketchPoint.geometry, 0.0001):
            point2 = line2.startSketchPoint.geometry
        elif point1.isEqualToByTolerance(line2.endSketchPoint.geometry, 0.0001):
            point2 = line2.endSketchPoint.geometry
        else:
            raise ValueError("The lines do not share a common point for fillet.")

    f = sketch.sketchCurves.sketchArcs.addFillet(line1, point1, line2, point2, radius)

    if add_dimension:
        sketch.sketchDimensions.addRadialDimension(f, point1)
    return f


def sketch_fitted_splines(
    sketch: adsk.fusion.Sketch, points: Iterable[Vector | adsk.core.Point3D | adsk.fusion.SketchPoint]
):
    """Add a fitted spline to the sketch using a list of points."""
    converted = [point3d(p) if isinstance(p, Vector) else p for p in points]
    return sketch.sketchCurves.sketchFittedSplines.add(collection(converted))


def sketch_arc_center_start_end(
    sketch: adsk.fusion.Sketch,
    center: Vector | adsk.core.Point3D,
    start: Vector | adsk.core.Point3D,
    end: Vector | adsk.core.Point3D,
):
    """Add an arc by center, start, and end points."""
    if isinstance(center, Vector):
        center = point3d(center)
    if isinstance(start, Vector):
        start = point3d(start)
    if isinstance(end, Vector):
        end = point3d(end)

    return sketch.sketchCurves.sketchArcs.addByCenterStartEnd(center, start, end)  # type: ignore[arg-type]


class DimensionOrientations:
    aligned = cast(
        adsk.fusion.DimensionOrientations,
        adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
    )
    horizontal = cast(
        adsk.fusion.DimensionOrientations,
        adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
    )
    vertical = cast(
        adsk.fusion.DimensionOrientations,
        adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
    )
