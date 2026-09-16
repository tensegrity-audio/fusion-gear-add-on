# Pure numerical routines extracted from the pinned MIT Study Gears engine.
from __future__ import annotations
from .guard import checkpoint
from math import asin, acos, atan, tan, sin, cos, pi, atan2, sqrt, ceil, log
from collections.abc import Iterable
from typing import Literal
from .vector import Vector
from .lib.function import minimize


class Params:
    def __init__(
        self,
        axes_angle: float,
        module: float,
        z1: int,
        z2: int,
        beta: float,  # helix angle
        addendum: float,
        dedendum: float,
        pressure_angle: float,
        width: float,
        backlash: float,
    ):
        # calculate transverse values for spiral gears
        self.sigma = axes_angle
        self.m = module / cos(beta)
        self.mf = dedendum * cos(beta)
        self.mk = addendum * cos(beta)
        self.alpha = atan(tan(pressure_angle) / cos(beta))
        self.beta = beta

        self.width = width
        self.backlash = backlash

        # larger gear is z1, smaller gear is z2
        self.z1 = max(z1, z2)
        self.z2 = min(z1, z2)

        self.calculate_params()

    def calculate_params(self):
        self.gamma_p1 = atan2(sin(self.sigma), self.z2 / self.z1 + cos(self.sigma))
        self.gamma_p2 = self.sigma - self.gamma_p1

        self.internal = 0
        if self.gamma_p1 > pi / 2:
            self.gamma_p1 = pi - self.gamma_p1
            self.internal = 1

        self.r = self.z1 / (2 * sin(self.gamma_p1))
        self.r0 = self.r * self.m
        self.rm = 1 / self.r

        self.gamma_f1 = self.gamma_p1 - self.mf * atan(self.rm)
        self.gamma_k1 = self.gamma_p1 + self.mk * atan(self.rm)
        self.gamma_t1 = self.gamma_p1 + self.mf * atan(self.rm)
        self.gamma_b1 = asin(cos(self.alpha) * sin(self.gamma_p1))

        self.gamma_f2 = self.gamma_p2 - self.mf * atan(self.rm)
        self.gamma_k2 = self.gamma_p2 + self.mk * atan(self.rm)
        self.gamma_t2 = self.gamma_p2 + self.mf * atan(self.rm)
        self.gamma_b2 = asin(cos(self.alpha) * sin(self.gamma_p2))

        if self.internal == 1:
            self.gamma_k1 = self.gamma_p1 + self.mf * atan(self.rm)
            self.gamma_f1 = max(self.gamma_f1, self.gamma_b1)

        self.axis1 = Vector(cos(self.gamma_p1), 0, sin(self.gamma_p1))
        self.axis2 = Vector(cos(self.gamma_p2), 0, -sin(self.gamma_p2))


def gear_curves(params: Params):
    """Generate the involute and trochoid curves for the two gears."""

    def trans(epsilon: float, v: Vector, axis: Vector, gamma_b: float):
        """transform v along base circle by angle specified by epsilon
        and then pushed back along the great circle by same distance"""
        axis = axis.normalize(cos(gamma_b))
        v = v.normalize()
        oq = v - axis
        om = oq.rotate_axis(axis, epsilon)
        oom = axis + om
        axis2 = oom - axis.normalize(1 / cos(gamma_b))
        op = oom.rotate_axis(axis2, epsilon * sin(gamma_b))
        return op

    def gamma2theta(gamma: float, gamma_b: float):
        """gamma_b is the angular radius of the base circle.
        gamma is the angular radius of the point of interest.
        theta is the angle around the axis of the gear
        between the point of interest and the original point."""
        varphi = acos(cos(gamma) / cos(gamma_b))
        return varphi / sin(gamma_b) - atan2(tan(varphi), sin(gamma_b))

    def gamma2epsilon(gamma: float, gamma_b: float):
        """epsilon is the angle of the gear rotation
        needed to bring the original point to the point of interest."""
        varphi = acos(cos(gamma) / cos(gamma_b))
        return varphi / sin(gamma_b)

    def spherical_involute(
        axis: Vector, v: Vector, gamma_b: float, gamma_s: float, gamma_e: float, n=20
    ):
        """v should be a point on the base circle.
        gamma_b is the angular radius of the base circle.
        returns a list of points on the involute curve
        from the angular radius gamma_s to gamma_e."""
        points: list[Vector] = []
        ts = gamma2epsilon(gamma_s, gamma_b)
        te = gamma2epsilon(gamma_e, gamma_b)
        for i in range(0, n + 1):
            checkpoint()
            t = ts + ((te - ts) / n) * i
            points.append(trans(t, v, axis, gamma_b))
        return points

    # calculate the trace of point t1 on the rotational coordinate system of gear2
    def spherical_trochoid(
        t1: Vector,  # tip point on the extended tip circle
        q2: Vector,  # original point on the base circle of the 2nd gear
        axis1: Vector,  # axis of the 1st gear
        axis2: Vector,  # axis of the 2nd gear
        z1: float,  # number of teeth of the 1st gear
        z2: float,  # number of teeth of the 2nd gear
        tooth2: list[Vector],  # involute curve of the 2nd gear
        gamma_b2: float,  # angular radius of the base circle of the 2nd gear
        gamma_f2: float,  # angular radius of the bottom circle of the 2nd gear
        n=10,
    ):
        def trochoid_core(t: float):
            return t1.rotate_axis(axis1, -t).rotate_axis(axis2, (-t / z2) * z1)

        # sweep t from 0 until getting out of the tip circle
        i = 0
        while True:
            checkpoint()
            t = (0.02 * (i * pi)) / sqrt(z1)
            if (trochoid_core(t) - axis2).norm() > (tooth2[-1] - axis2).norm():
                t1b = t  # tip circle
                break
            i += 1

        # bottom circle: find the point with minimum gamma
        t1a = minimize(0, t1b, lambda t: (trochoid_core(t) - axis2).norm())

        if gamma_b2 > gamma_f2:
            # cross section with the base circle
            t1c = minimize(
                t1a,
                t1b,
                lambda t: abs((trochoid_core(t) - axis2).norm() - (q2 - axis2).norm()),
            )
        else:
            # bottom circle
            t1c = t1a

        def distance_from_involute(t: float):
            """Measure the distance from the involute curve at the same gamma value"""
            v = trochoid_core(t)
            gamma = acos(v.dot(axis2))
            # involute curve of gear2
            u = trans(gamma2epsilon(gamma, gamma_b2), q2, axis2, gamma_b2)
            return (u - v).norm()

        # find the point on the trochoid curve that is closest to the involute curve
        # it may not a cross point but a tangent point.
        t1d = minimize(t1c, t1b, distance_from_involute)

        # use the part from bottom circle (t1a) to the contact point with involute (t1d)
        c1: list[Vector] = []  # trochoid curve
        for i in range(0, n + 1):
            checkpoint()
            t = t1a + ((t1d - t1a) * i) / n
            c1.append(trochoid_core(t))

        gamma = acos(c1[-1].dot(axis2))  # for contact point with involute curve
        return (c1, gamma)

    ext = params.rm * 0.2  # extension of the involute curve

    # p1 is a point on the base circle of the 1st gear
    p1 = Vector(x=1).rotate_axis(Vector(y=1), params.gamma_p1 - params.gamma_b1)
    # q1 is the point on the base circle of the 1st gear,
    # the involute curve from which pass through the reference point (1, 0, 0),
    # where the two gears touch each other on the reference circle.
    q1 = p1.rotate_axis(params.axis1, -gamma2theta(params.gamma_p1, params.gamma_b1))
    # get involute curve from q1,
    # from the base circle (gamma_b1) or the bottom circle (gamma_f1)
    # to the tip circle (gamma_t1).
    involute1 = spherical_involute(
        params.axis1,
        q1,
        params.gamma_b1,
        max(params.gamma_b1, params.gamma_f1),
        params.gamma_k1 + ext,
    )
    # t1 is the point at the cross section of the involute curve and the extended tip circle
    t1 = trans(gamma2epsilon(params.gamma_t1, params.gamma_b1), q1, params.axis1, params.gamma_b1)

    # same procedure for the 2nd gear
    p2 = Vector(x=1).rotate_axis(Vector(y=1), -(params.gamma_p2 - params.gamma_b2))
    q2 = p2.rotate_axis(params.axis2, -gamma2theta(params.gamma_p2, params.gamma_b2))
    involute2 = spherical_involute(
        params.axis2,
        q2,
        params.gamma_b2,
        max(params.gamma_b2, params.gamma_f2),
        params.gamma_k2 + ext,
    )
    t2 = trans(gamma2epsilon(params.gamma_t2, params.gamma_b2), q2, params.axis2, params.gamma_b2)

    # generate trochoid curve and determine the intersection with involute curve
    if params.internal != 1:
        trochoid1, gamma1 = spherical_trochoid(
            t2,
            q1,
            params.axis2,
            params.axis1,
            params.z2,
            params.z1,
            involute1,
            params.gamma_b1,
            params.gamma_f1,
        )
        involute1 = spherical_involute(
            params.axis1, q1, params.gamma_b1, gamma1, params.gamma_k1 + ext
        )
    else:
        trochoid1 = [involute1[0]]

    trochoid2, gamma2 = spherical_trochoid(
        t1,
        q2,
        params.axis1,
        params.axis2,
        params.z1,
        params.z2,
        involute2,
        params.gamma_b2,
        params.gamma_f2,
    )
    involute2 = spherical_involute(
        params.axis2, q2, params.gamma_b2, gamma2, params.gamma_k2 + ext
    )

    return trochoid1, involute1, trochoid2, involute2


def tooth_groove(
    params: Params,
    trochoid: list[Vector],
    involute: list[Vector],
    axis: Vector,
    z: float,
) -> list[Iterable[Vector]]:
    """Generate the tooth groove profile by scaling and
    connecting the involute and trochoid curves.
    Returns a list of curves that defines one closed loop."""

    r0 = params.r0
    m = params.m
    backlash = params.backlash
    internal = params.internal

    def apply_backlash(curve: list[Vector], axis: Vector, z: float):
        """Set back the curve by backlash around the axis."""

        def project(v: Vector):
            """Project p onto the plane normal to the axis and normalize."""
            return (v - axis.normalize(v.dot(axis))).normalize()

        def angle(p: Vector):
            """Measure the angle around axis between p and x-axis."""
            return acos(project(p).dot(project(Vector(x=1))))

        # scale by r0 and apply backlash
        b = -backlash if internal else backlash
        curve = [r0 * p.rotate_axis(axis, b / (m * z / 2)) for p in curve]

        # if tip or bottom are overlapped, remove the part
        while len(curve) > 0 and angle(curve[0]) > pi / z / 2:
            checkpoint()
            curve.pop(0)
        while len(curve) > 0 and angle(curve[-1]) > pi / z / 2:
            checkpoint()
            curve.pop()
        return curve

    def generate_arc(
        axis: Vector,
        p1: Vector,
        p2: Vector,
        great_arc=False,
        n=6,
    ):
        """Generate an arc between two points on a sphere."""
        if great_arc:
            center = Vector()
        else:
            center = axis.normalize(axis.normalize().dot(p1))
        c: list[Vector] = []
        v1 = p1 - center
        v2 = p2 - center
        t = acos(v1.dot(v2) / (v1.norm() * v2.norm()))
        if abs(v1.rotate_axis(axis, -t) - v2) < abs(v1.rotate_axis(axis, t) - v2):
            t = -t  # determine the direction of the arc
        for j in range(0, n + 1):
            checkpoint()
            t2 = (t * j) / n
            c.append(center + v1.rotate_axis(axis, t2))
        return c

    trochoid1 = apply_backlash(trochoid, axis, z)
    involute1 = apply_backlash(involute, axis, z)
    involute2 = [p.flip_y().rotate_axis(axis, -pi / z) for p in involute1]
    trochoid2 = [p.flip_y().rotate_axis(axis, -pi / z) for p in trochoid1]
    bottom = generate_arc(axis, trochoid2[0], trochoid1[0])
    top = generate_arc(axis, involute2[-1], involute1[-1])
    return [
        reversed(involute1),
        reversed(trochoid1),
        reversed(bottom),
        trochoid2,
        involute2,
        top,
    ]
