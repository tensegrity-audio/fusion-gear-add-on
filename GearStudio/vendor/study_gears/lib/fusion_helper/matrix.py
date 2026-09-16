# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from ...guard import checkpoint

import adsk.core, adsk.fusion

from . import vector
from .vector3d import vector3d
from .point3d import point3d


def matrix_scale(
    x=1.0,
    y=1.0,
    z=1.0,
    base: adsk.core.Matrix3D | None = None,
):
    matrix = adsk.core.Matrix3D.create()
    matrix.setToAlignCoordinateSystems(
        point3d(),
        vector3d(x=1),
        vector3d(y=1),
        vector3d(z=1),
        point3d(),
        vector3d(x=x),
        vector3d(y=y),
        vector3d(z=z),
    )
    if base is None:
        return matrix
    base.transformBy(matrix)
    return base


def matrix_flip_axes(
    x: bool = False,
    y: bool = False,
    z: bool = False,
    base: adsk.core.Matrix3D | None = None,
):
    return matrix_scale(-1 if x else 1, -1 if y else 1, -1 if z else 1, base)


def matrix_wrap(
    transform: adsk.core.Matrix3D,
    matrix: adsk.core.Matrix3D,
):
    """Returns `inv(transform) * matrix * transform`."""
    result = transform.copy()
    result.invert()
    result.transformBy(matrix)
    result.transformBy(transform)
    return result


def matrix_wrap_inv(
    transform: adsk.core.Matrix3D,
    matrix: adsk.core.Matrix3D,
):
    """Returns `transform * matrix * inv(transform)`."""
    result = transform.copy()
    result.transformBy(matrix)
    inv = transform.copy()
    inv.invert()
    result.transformBy(inv)
    return result


def matrix_rotate(
    angle: float,
    axis: adsk.core.Vector3D | vector.Vector = adsk.core.Vector3D.create(z=1),
    center: adsk.core.Point3D | vector.Vector = adsk.core.Point3D.create(),
    translation: adsk.core.Vector3D | vector.Vector | None = None,
    base: adsk.core.Matrix3D | None = None,
):
    matrix = adsk.core.Matrix3D.create()
    if isinstance(axis, vector.Vector):
        axis = vector3d(axis.x, axis.y, axis.z)
    if isinstance(center, vector.Vector):
        center = point3d(center.x, center.y, center.z)
    if isinstance(translation, vector.Vector):
        translation = vector3d(translation.x, translation.y, translation.z)
    matrix.setToRotation(angle, axis, center)  # type: ignore[arg-type]
    if translation is not None:
        matrix.translation = translation  # type: ignore[assignment]
    if base is None:
        return matrix
    base.transformBy(matrix)
    return base


def matrix_translate(
    x: adsk.core.Vector3D | vector.Vector | float = 0,
    y: float = 0,
    z: float = 0,
    base: adsk.core.Matrix3D | None = None,
):
    matrix = adsk.core.Matrix3D.create()
    matrix.translation = vector3d(x, y, z)
    if base is None:
        return matrix
    base.transformBy(matrix)
    return base
