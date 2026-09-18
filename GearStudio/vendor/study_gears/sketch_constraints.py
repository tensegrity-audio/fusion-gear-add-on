"""Constraints for generated geometry, in its owning component's coordinates.

Calculated tooth curves are locked snapshots and regenerate through Update gear.
Simple circles use real driving dimensions, never Fix on a dimensioned circle.
No Autodesk imports here so the API boundary can be exercised without Fusion.
"""
from .guard import checkpoint

ATTRIBUTE_GROUP = "GearStudio"
DIAMETER_INPUT = "diameter_input"


def centered_circle(sketch, radius, point3d, expression=None, input_field=None):
    """Add an origin-coincident, diameter-driven circle (lengths in cm)."""
    circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(point3d(), radius)
    center = circle.centerSketchPoint
    if not center.isFullyConstrained:
        constraint = sketch.geometricConstraints.addCoincident(center, sketch.originPoint)
        if constraint is None:
            raise RuntimeError("Fusion could not constrain the circle to its local origin.")
    dimension = sketch.sketchDimensions.addDiameterDimension(
        circle, point3d(radius, radius, 0), isDriving=True,
    )
    if dimension is None or dimension.parameter is None:
        raise RuntimeError("Fusion could not create a driving diameter dimension.")
    dimension.parameter.expression = expression or f"{2 * radius:.17g} cm"
    if expression and input_field:
        attribute = dimension.attributes.add(ATTRIBUTE_GROUP, DIAMETER_INPUT, input_field)
        if attribute is None:
            raise RuntimeError("Fusion could not identify the gear's driving diameter.")
    if not circle.isFullyConstrained:
        raise RuntimeError("The generated diameter or center is still unconstrained.")
    return circle


def lock_generated_sketch(sketch):
    """Lock calculated snapshots, including free endpoints and spline points.

    A fixed curve alone can still have free sketch points. Solve first and fix
    only remaining freedom; do not add redundant fixes to dimensioned geometry.
    This helper must not be used on sketches intended for live dimension edits.
    """
    if sketch.isComputeDeferred:
        raise RuntimeError("Finish deferred sketch computation before constraining it.")
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


def require_constrained(sketch):
    if not sketch.isFullyConstrained:
        raise RuntimeError(f"Generated sketch '{sketch.name}' is not fully constrained. No gear was committed.")
