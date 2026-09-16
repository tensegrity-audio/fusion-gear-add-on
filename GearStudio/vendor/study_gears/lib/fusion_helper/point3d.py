# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from ...guard import checkpoint
import math

import adsk.core, adsk.fusion

from . import vector


def point3d(
    x: float | adsk.core.Point3D | adsk.core.Vector3D | vector.Vector = 0,
    y: float = 0,
    z: float = 0,
):
    if (
        isinstance(x, adsk.core.Point3D)
        or isinstance(x, adsk.core.Vector3D)
        or isinstance(x, vector.Vector)
    ):
        return adsk.core.Point3D.create(x.x, x.y, x.z)
    return adsk.core.Point3D.create(x, y, z)


def point3d_add(
    p1: adsk.core.Point3D, p2: adsk.core.Point3D | vector.Vector | adsk.core.Vector3D
):
    return point3d(p1.x + p2.x, p1.y + p2.y, p1.z + p2.z)


def point3d_mul(p1: adsk.core.Point3D, v: float):
    return point3d(p1.x * v, p1.y * v, p1.z * v)


def point3d_div(p1: adsk.core.Point3D, v: float):
    return point3d_mul(p1, 1 / v)


def point3d_polar(r: float, t: float = 0, z: float = 0):
    return point3d(r * math.cos(t), r * math.sin(t), z)
