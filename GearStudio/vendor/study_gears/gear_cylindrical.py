# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from .guard import checkpoint
from .sketch_constraints import centered_circle, fixed_reference_line, lock_generated_sketch, require_constrained
from collections.abc import Callable
from copy import copy
from math import atan, cos, tan, pi, ceil, trunc
import adsk.core, adsk.fusion

from . import gear_curve
from .lib import fusion_helper as fh
from .lib.fusion_helper import Vector


def gear_cylindrical(
    parent_occurrence: adsk.fusion.Occurrence,
    params: gear_curve.GearParams,
    thickness: float,
    beta: float,
    tip_fillet: float,
):
    z = params.z
    m = params.m

    # Create a new component by creating a new occurrence.
    occurrence = parent_occurrence.component.occurrences.addNewComponent(
        adsk.core.Matrix3D.create()
    ).createForAssemblyContext(parent_occurrence)
    comp = occurrence.component

    # Create a new sketch on the xy plane.
    sketch = comp.sketches.add(comp.xYConstructionPlane).createForAssemblyContext(occurrence)
    sketch.name = "Tooth groove profile"
    sketch.isComputeDeferred = True

    # Generate tooth profile with adjusted parameters for helical angle.
    # https://www.khkgears.co.jp/gear_technology/basic_guide/KHK365.html
    cos_beta = cos(beta)
    mn = m / cos_beta
    params_adjusted = copy(params)
    params_adjusted.m = mn
    params_adjusted.mk *= cos_beta
    params_adjusted.mf *= cos_beta
    params_adjusted.fillet *= cos_beta
    params_adjusted.rc *= cos_beta
    params_adjusted.alpha = atan(tan(params.alpha) / cos_beta)
    params_adjusted.shift *= cos_beta
    params_adjusted.backlash /= cos_beta
    params_adjusted.backlash *= -1 if params.inner else 1
    curves = gear_curve.gear_curve(params_adjusted, tip_fillet * cos_beta)
    # curves: [(curve, tangent1, tangent2), ...]

    # Point on the extended tip circle (extended for tip_fillet)
    if isinstance(curves[0][0], Vector):
        pt = curves[0][0] + Vector.polar(curves[0][3], curves[0][1])
    else:
        pt = curves[0][0](curves[0][1])

    # Draw extended tip circle
    tip_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
        fh.point3d(),
        pt.norm(),
    )
    tip_circle.isFixed = True

    # draw groove shape
    lines1 = draw_part(sketch, curves, pi / z)
    sketch.geometricConstraints.addCoincident(lines1[0][1], tip_circle)
    lines2 = draw_part(sketch, curves, -pi / z, flip_y=True)
    sketch.geometricConstraints.addCoincident(lines2[-1][2], tip_circle)
    for curve in sketch.sketchCurves:
        checkpoint()
        curve.isFixed = True

    # bottom arc
    if lines1[-1][2].geometry.y != lines2[0][1].geometry.y:
        sketch.sketchCurves.sketchArcs.addByCenterStartEnd(
            fh.point3d(),
            lines2[0][1],
            lines1[-1][2],
        ).isFixed = True

    # extend the groove shape slightly out of the tip circle
    l1 = sketch.sketchCurves.sketchLines.addByTwoPoints(
        lines1[0][1],
        fh.point3d(Vector(lines1[0][1].geometry) * 1.01),
    )
    l1.isFixed = True
    l2 = sketch.sketchCurves.sketchLines.addByTwoPoints(
        lines2[-1][2],
        fh.point3d(Vector(lines2[-1][2].geometry) * 1.01),
    )
    l2.isFixed = True
    sketch.sketchCurves.sketchArcs.addByCenterStartEnd(
        fh.point3d(),
        l2.endSketchPoint,
        l1.endSketchPoint,
    ).isFixed = True

    sketch.isComputeDeferred = False
    lock_generated_sketch(sketch)

    # extrude the tip circle to generate a disk
    profiles = sorted(sketch.profiles, key=lambda p: p.boundingBox.minPoint.x)[
        0 : 2 if tip_fillet == 0 else 3
    ]
    disk = fh.comp_extrude(
        comp, profiles, fh.FeatureOperations.new_body, thickness, True, True
    ).bodies[0]

    # draw the axis
    sketch2 = comp.sketches.add(comp.xYConstructionPlane)
    sketch2.name = "Pitch circle and shaft axis"
    center_axis = fixed_reference_line(
        sketch2, fh.point3d(z=-thickness / 2), fh.point3d(z=thickness / 2)
    )

    # draw the reference circle
    circle = centered_circle(sketch2, mn * z / 2, fh.point3d)
    circle.isConstruction = True
    require_constrained(sketch2)

    # cut the groove from the disk
    teeth_profiles = sorted(  # two profiles from right
        sketch.profiles,
        key=lambda p: p.areaProperties().centroid.x,
        reverse=True,
    )[0:2]
    if beta == 0:
        # for non-helical gears, simply extrude the groove shape
        cut = fh.FeatureOperations.new_body
        tooth_feature = fh.comp_extrude(
            comp, teeth_profiles, cut, thickness, True, True
        )
    else:
        # Sweeping the groove profile with rotation angle is theoretically
        # the best way to cut a helical tooth shape. However, we found it
        # results in inaccurate results.
        # So, to workaround it, we use loft feature instead.
        #
        # # If we sweep the groove shape both in the thickness direction,
        # # we will have a seam at the center.
        # # To avoid it, we first move the shape to one end of the thickness
        # # and sweep.
        # patch1 = fh.comp_patch(comp, teeth_profiles, fh.FeatureOperations.new_body)
        # matrix = fh.matrix_rotate(
        #     -thickness * tan(beta) / (mn * z),
        #     comp.zConstructionAxis.geometry.direction,
        #     comp.originConstructionPoint.geometry,
        #     fh.vector3d(0, 0, -thickness / 2),
        # )
        # patch1 = fh.comp_move_free(comp, patch1.bodies, matrix)
        #
        # tooth_feature = fh.comp_sweep(
        #         comp,
        #         patch1.bodies[0].faces[0],
        #         center_axis,
        #         fh.FeatureOperations.cut,
        #         participants=[disk],
        #         twist=2 * thickness * tan(beta) / (mn * z),
        #     )
        # )
        #
        # fh.comp_remove(comp, patch1.bodies)

        # create rotated patches for loft
        patches: list[adsk.fusion.BRepBody] = []
        n = max(5, ceil(abs(thickness * tan(beta) / (mn * z)) / (2 * pi / 18)))
        for i in range(n):
            checkpoint()
            zz = i / (n - 1) * thickness / 2
            if i == 0:
                patches.append(
                    fh.comp_patch(comp, teeth_profiles, fh.FeatureOperations.new_body).bodies[0]
                )
            else:
                patches.append(fh.comp_copy(comp, patches[i-1]).bodies[0])
                matrix = fh.matrix_rotate(
                    -2 * zz * tan(beta) / (mn * z),
                    comp.zConstructionAxis.geometry.direction,
                    comp.originConstructionPoint.geometry,
                    fh.vector3d(
                        fh.Vector(comp.zConstructionAxis.geometry.direction).normalize(-zz)
                    ),
                )
                fh.comp_move_free(comp, patches[-1], matrix, occurrence)

                patches.insert(
                    0,
                    fh.comp_copy(comp, patches[i-1]).bodies[0]
                )
                matrix = fh.matrix_rotate(
                    2 * zz * tan(beta) / (mn * z),
                    comp.zConstructionAxis.geometry.direction,
                    comp.originConstructionPoint.geometry,
                    fh.vector3d(
                        fh.Vector(comp.zConstructionAxis.geometry.direction).normalize(zz)
                    ),
                )
                fh.comp_move_free(comp, patches[0], matrix, occurrence)

        tooth_feature = fh.comp_loft(
            comp, fh.FeatureOperations.new_body, [p.faces[0] for p in patches]
        )
        fh.comp_remove(comp, patches)

    # Pattern the actual cutter solid. Repeating the dependent loft-cut feature
    # can leave shallow seams and a single real groove in some Fusion versions.
    # Body patterning gives every instance an explicit rigid transformation.
    tooth_feature.name = "Tooth cutter"
    cutters = [body for body in tooth_feature.bodies if body.isSolid]
    if len(cutters) != 1:
        raise RuntimeError("The tooth cutter must be one solid before patterning.")
    pattern = fh.comp_circular_pattern(comp, cutters, comp.zConstructionAxis, trunc(z))
    pattern.name = "Repeat tooth cutters"
    # Feature.bodies can omit the seed body. Gather the live bodies instead.
    tools = [body for body in comp.bRepBodies if body.isSolid and body != disk]
    if len(tools) != trunc(z):
        raise RuntimeError("Fusion did not generate the requested number of tooth cutters.")
    cut = fh.comp_combine(comp, disk, tools, fh.FeatureOperations.cut)
    cut.name = "Cut all tooth spaces"

    # show the axis and reference circle
    sketch2.isVisible = True
    sketch.isVisible = True


def draw_part(
    sketch: adsk.fusion.Sketch,
    curves: list[tuple[Callable[[float], Vector] | Vector, float, float, int | float]],
    rot: float,
    last: adsk.fusion.SketchPoint | None = None,
    flip_y=False,
):
    def point3d(v: Vector):
        if not flip_y:
            return fh.point3d(v.rotate(rot))
        else:
            return fh.point3d(v.flip_y().rotate(rot))

    result: list[
        tuple[
            adsk.fusion.SketchArc | adsk.fusion.SketchFittedSpline,
            adsk.fusion.SketchPoint,
            adsk.fusion.SketchPoint,
        ]
    ] = []
    for c in reversed(curves) if flip_y else curves:
        checkpoint()
        if not flip_y:
            s = c[1]
            e = c[2]
        else:
            s = c[2]
            e = c[1]
        if isinstance(c[0], Vector):
            # draw arc
            # (center, start, end, radius)
            arc = sketch.sketchCurves.sketchArcs.addByCenterStartSweep(
                point3d(c[0]),
                point3d(c[0] + Vector.polar(c[3], s)) if last is None else last,
                e - s if not flip_y else s - e,
            )
            if (e - s if not flip_y else s - e) > 0:
                result.append((arc, arc.startSketchPoint, arc.endSketchPoint))
            else:
                result.append((arc, arc.endSketchPoint, arc.startSketchPoint))
        else:
            # draw parametric curve
            # c = (func, ts, te, n_points)

            def curve(func: Callable[[float], Vector], s: float, e: float, n: int):
                points = [func(s + (e - s) * i / (n * 30 - 1)) for i in range(n * 30)]
                length = [0]
                for i in range(1, len(points)):
                    checkpoint()
                    length.append(length[-1] + (points[i] - points[i - 1]).norm())
                result = [points[0]]
                j = 0
                for i in range(1, n):
                    checkpoint()
                    l = length[-1] * (i / (n - 1))
                    while length[j] < l:
                        checkpoint()
                        j += 1
                    result.append(points[j])
                return result

            points = curve(c[0], s, e, int(c[3]))

            points3d = [point3d(p) for p in points]
            if last is not None:
                points3d[0] = last
            spline = sketch.sketchCurves.sketchFittedSplines.add(fh.collection(points3d))

            # add tangent constraints
            delta = (e - s) / c[3] / 1000

            pss = points[0] + (c[0](s + delta) - points[0]) * 500
            line = sketch.sketchCurves.sketchLines.addByTwoPoints(
                spline.startSketchPoint, point3d(pss)
            )
            line.isConstruction = True
            line.isFixed = True
            sketch.geometricConstraints.addTangent(spline, line)

            pee = points[-1] + (c[0](e - delta) - points[-1]) * 500
            line = sketch.sketchCurves.sketchLines.addByTwoPoints(
                spline.endSketchPoint, point3d(pee)
            )
            line.isConstruction = True
            line.isFixed = True
            sketch.geometricConstraints.addTangent(spline, line)

            result.append((spline, spline.startSketchPoint, spline.endSketchPoint))

        last = result[-1][2]

    return result
