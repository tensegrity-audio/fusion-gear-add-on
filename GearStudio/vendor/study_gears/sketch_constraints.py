"""Constraints for generated geometry, in its owning component's coordinates.

Calculated tooth curves are locked snapshots and regenerate through Update gear.
Simple circles use real driving dimensions, never Fix on a dimensioned circle.
No Autodesk imports here so the API boundary can be exercised without Fusion.
"""
from .guard import checkpoint
from math import isclose

ATTRIBUTE_GROUP = "GearStudio"
DIAMETER_INPUT = "diameter_input"


class SketchConstraintError(RuntimeError):
    """A construction/solver failure, not invalid user gear dimensions."""


def centered_circle(sketch, radius, point3d, expression=None, input_field=None):
    """Fix the center locally and drive only the diameter (lengths in cm).

    Do not use the circle's aggregate isFullyConstrained flag as a build gate.
    Check the actual center, driving dimension and evaluated radius instead.
    """
    circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(point3d(), radius)
    center = circle.centerSketchPoint
    center.isFixed = True
    position = center.geometry
    if not center.isFixed or any(abs(value) > 1e-8 for value in (position.x, position.y, position.z)):
        raise SketchConstraintError(f"Sketch '{sketch.name}': Fusion could not fix the circle center at the local origin.")
    dimension = sketch.sketchDimensions.addDiameterDimension(
        circle, point3d(radius, radius, 0), isDriving=True,
    )
    if dimension is None or dimension.parameter is None:
        raise SketchConstraintError(f"Sketch '{sketch.name}': Fusion could not create a driving diameter dimension.")
    dimension.parameter.expression = expression or f"{2 * radius:.17g} cm"
    if expression and input_field:
        attribute = dimension.attributes.add(ATTRIBUTE_GROUP, DIAMETER_INPUT, input_field)
        if attribute is None:
            raise SketchConstraintError("Fusion could not identify the gear's driving diameter.")
    if (not dimension.isDriving or not isclose(dimension.parameter.value, 2 * radius, rel_tol=1e-8, abs_tol=1e-8)
            or not isclose(circle.radius, radius, rel_tol=1e-8, abs_tol=1e-8)):
        raise SketchConstraintError(f"Sketch '{sketch.name}': Fusion did not apply the requested driving diameter.")
    return circle


def lock_generated_sketch(sketch):
    """Lock calculated snapshots, including free endpoints and spline points.

    A fixed curve alone can still have free sketch points. Solve first and fix
    only remaining freedom; do not add redundant fixes to dimensioned geometry.
    This helper must not be used on sketches intended for live dimension edits.
    """
    if sketch.isComputeDeferred:
        raise SketchConstraintError("Finish deferred sketch computation before constraining it.")
    for curve in sketch.sketchCurves:
        checkpoint()
        if not curve.isFixed and not curve.isFullyConstrained:
            curve.isFixed = True
    for point in sketch.sketchPoints:
        checkpoint()
        if not point.isFullyConstrained:
            point.isFixed = True
    require_constrained(sketch)


def fixed_reference_line(sketch, start, end):
    """Create a construction line with both endpoints locked in local space."""
    line = sketch.sketchCurves.sketchLines.addByTwoPoints(start, end)
    line.isConstruction = True
    for point in (line.startSketchPoint, line.endSketchPoint):
        if not point.isFullyConstrained:
            point.isFixed = True
    if not line.isFullyConstrained:
        line.isFixed = True
    return line


def require_constrained(sketch, checked_circles=()):
    """Accept circles verified by centered_circle without trusting aggregate flags.

    All other curves and points must still report fixed or fully constrained.
    The explicit whitelist belongs to this build call, never persisted or global.
    """
    if sketch.isFullyConstrained:
        return
    for curve in sketch.sketchCurves:
        if any(curve == checked for checked in checked_circles):
            continue
        if not curve.isFixed and not curve.isFullyConstrained:
            raise SketchConstraintError(f"Sketch '{sketch.name}': a generated curve remains unconstrained.")
    for point in sketch.sketchPoints:
        if not point.isFixed and not point.isFullyConstrained:
            raise SketchConstraintError(f"Sketch '{sketch.name}': a generated point remains unconstrained.")
