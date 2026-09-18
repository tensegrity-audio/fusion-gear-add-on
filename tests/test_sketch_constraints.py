"""Sketch degree-of-freedom contracts, using a small solver boundary substitute.

These establish requested constraints, expression binding and rejection paths.
They do not establish how Fusion's native solver handles every fitted spline.
"""
from types import SimpleNamespace
import unittest

from test_document import Attributes
from GearStudio.core.expressions import evaluate
from GearStudio.vendor.study_gears import sketch_constraints as sc


def point3d(x=0, y=0, z=0): return (x, y, z)


class Point:
    def __init__(self, position=(0, 0, 0)):
        self.position = position
        self.isFixed = False
        self.coincident = None
    @property
    def isFullyConstrained(self):
        return self.isFixed or (self.coincident is not None and self.coincident.isFullyConstrained)


class Circle:
    def __init__(self, center, radius):
        self.centerSketchPoint = Point(center)
        self.radius = radius
        self.dimension = None
        self.isFixed = False
    @property
    def isFullyConstrained(self):
        return self.centerSketchPoint.isFullyConstrained and self.dimension is not None


class Line:
    def __init__(self, start, end):
        self.startSketchPoint, self.endSketchPoint = Point(start), Point(end)
        self.isFixed = False
    @property
    def isFullyConstrained(self):
        # Fix on a curve does not by itself constrain the endpoint objects.
        return self.startSketchPoint.isFullyConstrained and self.endSketchPoint.isFullyConstrained


class Curves(list):
    def __init__(self, owner):
        super().__init__(); self.owner = owner
        self.sketchCircles = SimpleNamespace(addByCenterRadius=self.circle)
        self.sketchLines = SimpleNamespace(addByTwoPoints=self.line)
    def circle(self, center, radius):
        circle = Circle(center, radius)
        self.append(circle); self.owner.sketchPoints.append(circle.centerSketchPoint)
        return circle
    def line(self, start, end):
        line = Line(start, end)
        self.append(line)
        self.owner.sketchPoints.extend((line.startSketchPoint, line.endSketchPoint))
        return line


class Sketch:
    def __init__(self):
        self.name = 'Generated test sketch'
        self.isComputeDeferred = False
        self.originPoint = Point(); self.originPoint.isFixed = True
        self.sketchPoints = [self.originPoint]
        self.sketchCurves = Curves(self)
        self.dimensions = []
        self.geometricConstraints = SimpleNamespace(addCoincident=self.coincident)
        self.sketchDimensions = SimpleNamespace(addDiameterDimension=self.diameter)
    def coincident(self, point, target):
        point.coincident = target
        return object()
    def diameter(self, circle, text_point, isDriving):
        if circle.isFixed:
            raise RuntimeError('Fix and a driving diameter overconstrain the circle')
        if not isDriving:
            raise RuntimeError('A measurement cannot control this diameter')
        dimension = SimpleNamespace(parameter=SimpleNamespace(expression=''), attributes=Attributes())
        circle.dimension = dimension; self.dimensions.append(dimension)
        return dimension
    @property
    def isFullyConstrained(self):
        return all(item.isFullyConstrained for item in [*self.sketchCurves, *self.sketchPoints])


class SketchConstraintTests(unittest.TestCase):
    def test_bore_has_local_center_and_live_named_diameter_without_fixed_radius(self):
        sketch = Sketch()
        circle = sc.centered_circle(sketch, .25, point3d, 'Bore_G7', 'bore')
        self.assertIs(circle.centerSketchPoint.coincident, sketch.originPoint)
        self.assertEqual(circle.dimension.parameter.expression, 'Bore_G7')
        self.assertEqual(circle.dimension.attributes.itemByName(sc.ATTRIBUTE_GROUP, sc.DIAMETER_INPUT).value, 'bore')
        self.assertFalse(circle.isFixed)
        self.assertTrue(sketch.isFullyConstrained)

    def test_preflight_ring_and_reference_diameters_use_explicit_cm_units(self):
        for radius in (.25, 1.2, 2.6):
            sketch = Sketch()
            circle = sc.centered_circle(sketch, radius, point3d)
            self.assertAlmostEqual(evaluate(circle.dimension.parameter.expression, 'mm'), radius * 20)
            self.assertIsNone(circle.dimension.attributes.itemByName(sc.ATTRIBUTE_GROUP, sc.DIAMETER_INPUT))
            self.assertTrue(sketch.isFullyConstrained)

    def test_axis_endpoints_cannot_translate_or_change_length_and_line_is_construction(self):
        sketch = Sketch()
        line = sc.fixed_reference_line(sketch, point3d(z=-.2), point3d(z=.2))
        self.assertEqual(line.startSketchPoint.position, (0, 0, -.2))
        self.assertEqual(line.endSketchPoint.position, (0, 0, .2))
        self.assertTrue(line.isConstruction)
        sc.require_constrained(sketch)

    def test_calculated_sketch_locks_free_endpoints_even_if_curve_is_already_fixed(self):
        sketch = Sketch()
        line = sketch.sketchCurves.line(point3d(), point3d(0, 1))
        line.isFixed = True
        self.assertFalse(sketch.isFullyConstrained)
        sc.lock_generated_sketch(sketch)
        self.assertTrue(sketch.isFullyConstrained)

    def test_constraint_failure_or_solver_free_geometry_cannot_be_committed(self):
        sketch = Sketch()
        sketch.geometricConstraints.addCoincident = lambda *args: None
        with self.assertRaisesRegex(RuntimeError, 'local origin'):
            sc.centered_circle(sketch, .25, point3d)
        with self.assertRaisesRegex(RuntimeError, 'not fully constrained'):
            sc.require_constrained(sketch)

    def test_missing_driving_dimension_and_deferred_solving_fail_explicitly(self):
        sketch = Sketch()
        sketch.sketchDimensions.addDiameterDimension = lambda *args, **kw: None
        with self.assertRaisesRegex(RuntimeError, 'driving diameter'):
            sc.centered_circle(sketch, .25, point3d)
        sketch.isComputeDeferred = True
        with self.assertRaisesRegex(RuntimeError, 'deferred sketch'):
            sc.lock_generated_sketch(sketch)


if __name__ == '__main__': unittest.main()
