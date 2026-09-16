# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from ...guard import checkpoint
import math

import adsk.core, adsk.fusion

from . import vector


def vector3d(
    x: float | adsk.core.Point3D | adsk.core.Vector3D | vector.Vector = 0,
    y: float = 0,
    z: float = 0,
):
    if (
        isinstance(x, adsk.core.Point3D)
        or isinstance(x, adsk.core.Vector3D)
        or isinstance(x, vector.Vector)
    ):
        return adsk.core.Vector3D.create(x.x, x.y, x.z)
    return adsk.core.Vector3D.create(x, y, z)


def vector3d_polar(r: float, t: float = 0):
    return vector3d(r * math.cos(t), r * math.sin(t))


def vector3d_neg(v: adsk.core.Vector3D):
    return vector3d(-v.x, -v.y, -v.z)


def vector3d_normalize(v: adsk.core.Vector3D, length: float = 1):
    result = v.copy()
    result.normalize()
    if length != 1:
        result.scaleBy(length)
    return result


def vector3d_add(
    p1: adsk.core.Vector3D, p2: adsk.core.Point3D | vector.Vector | adsk.core.Vector3D
):
    return vector3d(p1.x + p2.x, p1.y + p2.y, p1.z + p2.z)
