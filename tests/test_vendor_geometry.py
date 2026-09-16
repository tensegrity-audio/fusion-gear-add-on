"""Numerical checks on the actual vendored tooth engine, without Fusion.

These check geometry invariants and input semantics. They do not certify fitted
Fusion splines, generated B-rep solids or manufactured gear accuracy.
"""
import math
import unittest

from GearStudio.vendor.study_gears.gear_curve import GearParams, rack_geometry
from GearStudio.vendor.study_gears import math_bevel, math_crown, math_worm_wheel
from GearStudio.vendor.study_gears.guard import bounded
from GearStudio.vendor.study_gears.vector import vec


class NativeEngineMathTests(unittest.TestCase):
    def params(self, teeth=24, backlash=0):
        return GearParams(.1, teeth, math.radians(20), 0, .25, 1.25, 1, .25, backlash, False)

    def test_rack_fillet_tangent_lies_on_flank_and_circle(self):
        # The old script connected a clipped rack point to a circle. The true
        # tangent must satisfy both independent geometric constraints.
        for alpha in (math.radians(15), math.radians(20), math.radians(30)):
            for tool_radius in (.10, .20, .30):
                r1, _, centre, radius = rack_geometry(.1, alpha, tool_radius, 1.25, 1, .25, .005)
                tangent = centre + vec(-radius * math.sin(alpha), radius * math.cos(alpha))
                self.assertAlmostEqual((tangent - centre).norm(), radius, places=12)
                self.assertAlmostEqual((tangent.y - r1.y) / (tangent.x - r1.x), math.tan(alpha), places=12)

    def test_bevel_curves_stay_on_the_design_sphere(self):
        for spiral in (0, math.radians(20), math.radians(-20)):
            with bounded(seconds=3):
                p = math_bevel.Params(math.pi / 2, .1, 40, 20, spiral, 1, 1.25,
                                     math.radians(20), .4, .0025)
                t1, i1, t2, i2 = math_bevel.gear_curves(p)
                for axis, n, root, flank in ((p.axis1, p.z1, t1, i1), (p.axis2, p.z2, t2, i2)):
                    groove = math_bevel.tooth_groove(p, root, flank, axis, n)
                    self.assertGreaterEqual(len(groove), 4)
                    for curve in groove:
                        for point in curve:
                            self.assertTrue(all(math.isfinite(v) for v in (point.x, point.y, point.z)))
                            self.assertAlmostEqual(point.norm(), p.r0, places=9)

    def test_crown_section_points_lie_on_requested_radial_cylinder(self):
        with bounded(seconds=15, iterations=10000000):
            p = self.params(backlash=-.005)
            p.fillet = .4
            pinion = math_crown.generate_pinion_tooth(p)
            curves = math_crown.calc_tooth_profiles(pinion, p, 48, 0, 0)
            expected = .1 * 48 / 2
            self.assertEqual(len(curves), 2)
            for curve in curves:
                self.assertGreaterEqual(len(curve), 10)
                for point in curve:
                    self.assertAlmostEqual(math.hypot(point.x, point.y), expected, places=10)
                    self.assertTrue(math.isfinite(point.z))

    def test_wheel_tooth_thinning_has_correct_sign_and_normal_units(self):
        beta = math.asin(1 / 12)
        rp = .1 * 36 / (2 * math.cos(beta))

        def gap_at_reference(backlash):
            p = self.params(36, backlash)
            with bounded(seconds=15, iterations=10000000):
                shape = math_worm_wheel.worm_wheel_shape_at_height(0, p, beta, .6, 1)
            angles = []
            for a, b in zip(shape, shape[1:]):
                ra, rb = a.norm(), b.norm()
                if (ra - rp) * (rb - rp) <= 0 and ra != rb:
                    t = (rp - ra) / (rb - ra)
                    point = a * (1 - t) + b * t
                    angles.append(math.atan2(point.y, point.x))
            self.assertEqual(len(angles), 2)
            return (max(angles) - min(angles)) * rp

        change = gap_at_reference(.005) - gap_at_reference(0)
        expected = .005 / math.cos(beta)
        self.assertGreater(change, 0)
        # Finite envelope sampling causes a small numerical interpolation error.
        self.assertAlmostEqual(change, expected, delta=expected * .01)


if __name__ == "__main__":
    unittest.main()
