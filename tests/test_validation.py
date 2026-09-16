import copy
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'GearStudio'))
from core.catalog import FAMILIES, catalog, default_spec
from core.validation import MAX_COST, validate


def setup(kind='spur', **changes):
    spec = default_spec(kind)
    values = {key: float(text.split()[0]) for key, text in spec['parameters'].items()}
    for key, value in changes.items():
        values[key] = value
        spec['parameters'][key] = str(value)
    return spec, values


class ValidationTests(unittest.TestCase):
    def assert_code(self, result, code):
        self.assertFalse(result['valid'])
        self.assertIn(code, [item['code'] for item in result['issues']])

    def test_every_family_has_valid_defaults(self):
        for family in FAMILIES:
            with self.subTest(kind=family['id']):
                result = validate(*setup(family['id']))
                self.assertTrue(result['valid'], result['issues'])
                self.assertLessEqual(result['cost']['units'], MAX_COST)

    def test_nonfinite_and_non_numeric_inputs_are_rejected_without_throwing(self):
        for value in (math.nan, math.inf, -math.inf, 10 ** 1000, True, '1', [], None):
            for key in ('module', 'teeth', 'width', 'pressure_angle'):
                with self.subTest(value=repr(value)[:20], field=key):
                    spec, values = setup()
                    values[key] = value
                    self.assertFalse(validate(spec, values)['valid'])

    def test_invalid_definition_shapes(self):
        for definition in (None, [], 'spur', {'kind': []}, {'kind': 'missing'}, {'kind': 'spur', 'parameters': []}):
            self.assertFalse(validate(definition, {})['valid'])
        spec, values = setup()
        self.assertFalse(validate(spec, None)['valid'])

    def test_missing_field_and_overlong_expression(self):
        spec, values = setup()
        del values['module']
        self.assert_code(validate(spec, values), 'numeric_type')
        spec, values = setup()
        spec['parameters']['module'] = 'x' * 257
        self.assert_code(validate(spec, values), 'expression_length')

    def test_inputs_are_not_mutated(self):
        spec, values = setup('helical')
        spec['parameters']['module'] = 'shaftModule + clearance'
        original = copy.deepcopy((spec, values))
        validate(spec, values)
        self.assertEqual((spec, values), original)

    def test_fractional_teeth_and_zero_dimensions_fail(self):
        self.assert_code(validate(*setup(teeth=24.5)), 'integer')
        self.assert_code(validate(*setup(width=0)), 'range')
        self.assert_code(validate(*setup(module=0)), 'range')

    def test_bore_cannot_cross_tooth_roots(self):
        self.assert_code(validate(*setup(bore=22)), 'bore_clearance')
        self.assert_code(validate(*setup(bore=0.01)), 'tiny_bore')
        self.assertTrue(validate(*setup(bore=0))['valid'])

    def test_internal_ring_clearance_and_base_circle(self):
        self.assert_code(validate(*setup('internal_spur', outside_diameter=50)), 'ring_rim')
        self.assert_code(validate(*setup('internal_spur', teeth=24)), 'internal_base_circle')

    def test_helical_normal_module_and_tooth_thinning(self):
        spec, values = setup('helical', helix_angle=30, backlash=0.1)
        metrics = validate(spec, values)['metrics']
        self.assertAlmostEqual(metrics['pitch_diameter'], 24 / math.cos(math.radians(30)))
        self.assertAlmostEqual(metrics['transverse_pressure_angle'], math.degrees(math.atan(math.tan(math.radians(20)) / math.cos(math.radians(30)))))
        self.assertAlmostEqual(metrics['normal_tooth_thickness'], math.pi / 2 - 0.1)
        self.assertAlmostEqual(metrics['tooth_thickness'], (math.pi / 2 - 0.1) / math.cos(math.radians(30)))

    def test_signed_helix_changes_twist_not_diameter(self):
        positive = validate(*setup('helical', helix_angle=30))['metrics']
        negative = validate(*setup('helical', helix_angle=-30))['metrics']
        self.assertAlmostEqual(positive['pitch_diameter'], negative['pitch_diameter'])
        self.assertAlmostEqual(positive['twist_angle'], -negative['twist_angle'])
        self.assert_code(validate(*setup('helical', helix_angle=0)), 'zero_helix')

    def test_extreme_helix_rejected_by_work_envelope(self):
        self.assert_code(validate(*setup('helical', width=100, helix_angle=45)), 'twist_budget')

    def test_pointed_teeth_and_missing_generating_clearance(self):
        self.assert_code(validate(*setup(teeth=6, backlash=0.35, bore=0)), 'pointed_teeth')
        self.assert_code(validate(*setup(dedendum=1.1, addendum=1.1)), 'radial_clearance')

    def test_fillet_inputs_are_not_silently_clamped(self):
        self.assert_code(validate(*setup(addendum=1, dedendum=1.1, root_fillet=0.3)), 'fillet_clearance')
        self.assert_code(validate(*setup(pressure_angle=30, dedendum=1.6, root_fillet=0.35)), 'fillet_centreline')

    def test_rack_back_and_skew(self):
        self.assert_code(validate(*setup('rack', rack_height=1)), 'rack_back')
        self.assert_code(validate(*setup('helical_rack', teeth=1, width=8)), 'rack_skew')
        self.assertTrue(validate(*setup('rack', teeth=1))['valid'])

    def test_worm_lead_domain_and_hand(self):
        self.assert_code(validate(*setup('worm', module=4, worm_starts=4, worm_diameter=12)), 'worm_lead_limit')
        self.assert_code(validate(*setup('worm', worm_hand=0)), 'thread_hand')
        a = validate(*setup('worm', worm_hand=1))['metrics']
        b = validate(*setup('worm', worm_hand=-1))['metrics']
        self.assertAlmostEqual(a['worm_lead_angle'], -b['worm_lead_angle'])
        self.assertAlmostEqual(a['lead'], b['lead'])
        self.assert_code(validate(*setup('worm', width=2)), 'worm_length')

    def test_wheel_envelope(self):
        self.assert_code(validate(*setup('worm_wheel', width=10)), 'wheel_face_width')

    def test_bevel_collapsing_face_and_incompatible_cones(self):
        self.assert_code(validate(*setup('bevel', width=8)), 'bevel_face_width')
        self.assert_code(validate(*setup('bevel', teeth=100, mate_teeth=6, shaft_angle=120, bore=0)), 'pitch_cone')

    def test_crown_generating_pinion_domain(self):
        self.assert_code(validate(*setup('crown', teeth=24)), 'crown_pinion_clearance')
        self.assert_code(validate(*setup('crown', bore=45)), 'crown_bore')
        self.assert_code(validate(*setup('crown', width=10)), 'crown_radial_width')

    def test_complexity_budget_rejects_large_enveloped_wheel(self):
        self.assert_code(validate(*setup('worm_wheel', teeth=160)), 'complexity_budget')

    def test_catalog_is_detached_and_parameters_consumed(self):
        a, b = catalog(), catalog()
        a['fields']['module']['default'] = '99 mm'
        self.assertEqual(b['fields']['module']['default'], '1 mm')
        for kind in ('rack', 'helical_rack', 'worm', 'bevel', 'spiral_bevel', 'crown'):
            self.assertNotIn('profile_shift', default_spec(kind)['parameters'])
        for kind in ('internal_spur', 'internal_helical', 'internal_herringbone', 'bevel', 'spiral_bevel', 'crown'):
            self.assertNotIn('root_fillet', default_spec(kind)['parameters'])


if __name__ == '__main__':
    unittest.main()
