import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'GearStudio'))
from core.catalog import FAMILIES, default_spec
from core.profiles import circle, involute_point, preview
from core.validation import MAX_PREVIEW_POINTS, validate


def setup(kind='spur', **changes):
    spec = default_spec(kind)
    values = {key: float(text.split()[0]) for key, text in spec['parameters'].items()}
    values.update(changes)
    for key, value in changes.items():
        spec['parameters'][key] = str(value)
    return spec, values


class GeometryTests(unittest.TestCase):
    def test_analytic_involute_radius_and_base_point(self):
        self.assertEqual(involute_point(10, 0), [10, 0])
        for t in (0.01, 0.2, 1.0, 2.0):
            x, y = involute_point(10, t)
            self.assertAlmostEqual(math.hypot(x, y), 10 * math.sqrt(1 + t * t), places=11)
            self.assertAlmostEqual(math.atan2(y, x), t - math.atan(t), places=11)

    def test_invalid_curve_domains(self):
        for r, t in ((0, 1), (-1, 1), (1, -1), (math.inf, 1), (1, math.nan)):
            with self.assertRaises(ValueError):
                involute_point(r, t)
        with self.assertRaises(ValueError):
            circle(0)

    def test_all_family_previews_bounded_finite_and_without_zero_edges(self):
        for family in FAMILIES:
            with self.subTest(kind=family['id']):
                result = preview(*setup(family['id']))
                self.assertTrue(result['valid'])
                self.assertLessEqual(result['pointCount'], MAX_PREVIEW_POINTS)
                self.assertGreater(result['bounds'][2], result['bounds'][0])
                self.assertGreater(result['bounds'][3], result['bounds'][1])
                for path in result['paths']:
                    points = path['points']
                    self.assertTrue(all(math.isfinite(c) for point in points for c in point))
                    pairs = list(zip(points, points[1:]))
                    if path['closed']:
                        pairs.append((points[-1], points[0]))
                    self.assertTrue(all(math.dist(a, b) > 1e-8 for a, b in pairs))

    def test_invalid_inputs_do_not_generate_curve(self):
        result = preview(*setup(teeth=0))
        self.assertFalse(result['valid'])
        self.assertEqual(result['paths'], [])

    def test_cylindrical_outline_matches_reference_tip_and_root(self):
        spec, values = setup()
        result = preview(spec, values)
        metrics = validate(spec, values)['metrics']
        radial = [math.hypot(*p) for p in result['paths'][0]['points']]
        self.assertAlmostEqual(max(radial), metrics['tip_diameter'] / 2, places=4)
        self.assertAlmostEqual(min(radial), metrics['root_diameter'] / 2, places=3)
        self.assertFalse(result['simplified'])

    def test_internal_cavity_and_outside_ring_are_distinct_loops(self):
        spec, values = setup('internal_spur')
        result = preview(spec, values)
        self.assertEqual(result['paths'][0]['role'], 'outline')
        self.assertEqual(result['paths'][1]['role'], 'cutout')
        outer = min(math.hypot(*p) for p in result['paths'][0]['points'])
        cavity = max(math.hypot(*p) for p in result['paths'][1]['points'])
        self.assertGreater(outer - cavity, 1)

    def test_cylindrical_repetition_has_tooth_pitch_symmetry(self):
        points = preview(*setup())['paths'][0]['points']
        tooth_samples = len(points) // 24
        self.assertEqual(len(points) % 24, 0)
        c, s = math.cos(2 * math.pi / 24), math.sin(2 * math.pi / 24)
        for i in range(tooth_samples):
            x, y = points[i]
            expected = [x * c - y * s, x * s + y * c]
            self.assertLess(math.dist(expected, points[i + tooth_samples]), 1e-7)

    def test_large_preview_remains_bounded(self):
        result = preview(*setup(teeth=160))
        self.assertTrue(result['valid'])
        self.assertLessEqual(result['pointCount'], MAX_PREVIEW_POINTS)

    def test_spatial_envelopes_labeled_honestly(self):
        for kind in ('worm', 'worm_wheel', 'bevel', 'spiral_bevel', 'crown'):
            result = preview(*setup(kind))
            self.assertTrue(result['simplified'])
            self.assertIn('envelope', result['label'])
            self.assertIn('after build', result['label'])

    def test_normal_module_section_widens_with_helix(self):
        spur = preview(*setup())
        helical = preview(*setup('helical'))
        self.assertGreater(helical['bounds'][2], spur['bounds'][2])


if __name__ == '__main__':
    unittest.main()
