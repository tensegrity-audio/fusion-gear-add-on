"""Regression for the reported mostly cylindrical gear, using geometric oracles.

These classify sampled 2D engine profiles extruded with the requested twist.
Actual ACIS solid construction still requires Fusion acceptance.
"""
import math
from types import SimpleNamespace
import unittest

from GearStudio.core.catalog import default_spec, FIELDS
from GearStudio.core.expressions import evaluate
from GearStudio.core.profiles import _generated_cylindrical
from GearStudio.fusion.builder import verify_tooth_spaces, BuildError


ADSK = SimpleNamespace(
    core=SimpleNamespace(Point3D=SimpleNamespace(create=lambda x,y,z: (x,y,z))),
    fusion=SimpleNamespace(PointContainment=SimpleNamespace(PointInsidePointContainment=0, PointOutsidePointContainment=2)))


def contains_polygon(points, x, y):
    inside = False
    previous = points[-1]
    for current in points:
        x1, y1 = previous; x2, y2 = current
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1:
            inside = not inside
        previous = current
    return inside


class ToothSpaceTests(unittest.TestCase):
    def values(self, kind):
        spec = default_spec(kind)
        return {field: evaluate(expression, FIELDS[field]['unit']) for field, expression in spec['parameters'].items()}

    def test_all_six_default_cylindrical_profiles_pass_with_twist(self):
        for kind in ('spur','helical','herringbone','internal_spur','internal_helical','internal_herringbone'):
            with self.subTest(kind=kind):
                values = self.values(kind)
                outline = _generated_cylindrical(kind, values)
                beta = math.radians(values.get('helix_angle',0))
                radius = values['module'] * values['teeth'] / (2 * math.cos(beta))
                def classify(point):
                    x,y,z = (coordinate * 10 for coordinate in point)
                    axial = abs(z)-values['width']/4 if 'herringbone' in kind else z
                    angle = -axial * math.tan(beta) / radius
                    x,y = x*math.cos(angle)-y*math.sin(angle), x*math.sin(angle)+y*math.cos(angle)
                    inside = contains_polygon(outline,x,y)
                    if kind.startswith('internal_'): inside = not inside
                    return 0 if inside else 2
                verify_tooth_spaces(SimpleNamespace(pointContainment=classify), kind, values, ADSK)

    def test_reported_cylinder_with_single_groove_is_rejected(self):
        values = self.values('helical')
        def single_groove(point):
            angle = math.atan2(point[1], point[0]) % (2*math.pi)
            return 2 if angle < math.pi/values['teeth'] else 0
        with self.assertRaisesRegex(BuildError, 'pattern is incomplete'):
            verify_tooth_spaces(SimpleNamespace(pointContainment=single_groove), 'helical', values, ADSK)

    def test_flat_cylinder_and_unknown_containment_are_rejected(self):
        for state in (0, 2, 3):
            with self.subTest(state=state), self.assertRaises(BuildError):
                verify_tooth_spaces(SimpleNamespace(pointContainment=lambda _: state), 'herringbone', self.values('herringbone'), ADSK)


if __name__ == '__main__': unittest.main()
