# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from ...guard import checkpoint
from collections.abc import Iterable
from typing import TypeVar, cast

import adsk.core, adsk.fusion
from .vector import Vector
from .vector3d import vector3d
from .point3d import point3d






def value_input(v: str | float | bool | int | adsk.core.Base):
    if isinstance(v, str):
        return adsk.core.ValueInput.createByString(v)
    if isinstance(v, bool):
        return adsk.core.ValueInput.createByBoolean(v)
    if isinstance(v, float) or isinstance(v, int):
        return adsk.core.ValueInput.createByReal(v)
    return adsk.core.ValueInput.createByObject(v)


def collection(arg: adsk.core.Base | Iterable[adsk.core.Base]):
    if isinstance(arg, Iterable):
        return adsk.core.ObjectCollection.createWithArray(list(arg))
    return adsk.core.ObjectCollection.createWithArray([arg])


def app_refresh():
    checkpoint(force=True)




def camera_setup(
    eye_or_cam: Vector | adsk.core.Camera | None = None,
    target: Vector | None = None,
    up: Vector | None = None,
    perspective: float = 0.0,
    smooth: bool = True,
    occurrence: adsk.fusion.Occurrence | None = None,
):
    app = adsk.core.Application.get()
    view = app.activeViewport
    cam = view.camera
    previous = adsk.core.Camera.create()
    previous.cameraType = cam.cameraType
    previous.isSmoothTransition = cam.isSmoothTransition
    previous.isFitView = cam.isFitView
    previous.eye = cam.eye.copy()
    previous.target = cam.target.copy()
    previous.upVector = cam.upVector.copy()
    previous.perspectiveAngle = cam.perspectiveAngle
    if cam.cameraType == adsk.core.CameraTypes.OrthographicCameraType:
        _, width, height = cam.getExtents()
        previous.setExtents(width, height)

    if isinstance(eye_or_cam, adsk.core.Camera):
        cam = eye_or_cam
        return previous
    eye = eye_or_cam

    T = TypeVar("T", adsk.core.Point3D, adsk.core.Vector3D)

    def transform(p: T) -> T:
        if occurrence is None:
            return p
        p.transformBy(occurrence.transform2)
        return p

    if eye is not None:
        cam.eye = transform(point3d(eye))
    if target is not None:
        cam.target = transform(point3d(target))
    if up is not None:
        cam.upVector = transform(vector3d(up))
    cam.isSmoothTransition = smooth
    if perspective > 0:
        cam.perspectiveAngle = perspective
    view.camera = cam

    return previous
