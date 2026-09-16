# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from ...guard import checkpoint
import adsk.core, adsk.fusion
from typing import cast

from .vector import Vector
from .point3d import point3d, point3d_add, point3d_div
from .sketch import DimensionOrientations


def dim_distance(
    point1: adsk.fusion.SketchPoint,
    point2: adsk.fusion.SketchPoint,
    orientation: adsk.fusion.DimensionOrientations | int,
    text_point: Vector | adsk.core.Point3D | None = None,
    is_driving: bool = True,
):
    if isinstance(text_point, Vector):
        text_point = point3d(text_point)
    if text_point is None:
        text_point = point3d_div(point3d_add(point1.geometry, point2.geometry), 2.0)
    return point1.parentSketch.sketchDimensions.addDistanceDimension(
        point1,
        point2,
        cast(adsk.fusion.DimensionOrientations, orientation),
        cast(adsk.core.Point3D, text_point),
        is_driving,
    )


def dim_distance_horizontal(
    point1: adsk.fusion.SketchPoint,
    point2: adsk.fusion.SketchPoint,
    text_point: Vector | adsk.core.Point3D | None = None,
    is_driving: bool = True,
):
    """Add a horizontal dimension between two points."""
    return dim_distance(
        point1,
        point2,
        DimensionOrientations.horizontal,
        text_point,
        is_driving,
    )


def dim_distance_vertical(
    point1: adsk.fusion.SketchPoint,
    point2: adsk.fusion.SketchPoint,
    text_point: Vector | adsk.core.Point3D | None = None,
    is_driving: bool = True,
):
    """Add a horizontal dimension between two points."""
    return dim_distance(
        point1,
        point2,
        DimensionOrientations.vertical,
        text_point,
        is_driving,
    )


def dim_distance_aligned(
    point1: adsk.fusion.SketchPoint,
    point2: adsk.fusion.SketchPoint,
    text_point: Vector | adsk.core.Point3D | None = None,
    is_driving: bool = True,
):
    """Add a horizontal dimension between two points."""
    return dim_distance(
        point1,
        point2,
        DimensionOrientations.aligned,
        text_point,
        is_driving,
    )


def dim_radial(
    curve: adsk.fusion.SketchArc | adsk.fusion.SketchCircle,
    text_point: Vector | adsk.core.Point3D | None = None,
    is_driving: bool = True,
):
    """Add a radial dimension to an arc or circle."""
    if isinstance(text_point, Vector):
        text_point = point3d(text_point)
    return curve.parentSketch.sketchDimensions.addRadialDimension(
        curve,
        (
            cast(adsk.core.Point3D, text_point)
            if text_point
            else curve.centerSketchPoint.geometry
        ),
        is_driving,
    )


def dim_angle(
    line1: adsk.fusion.SketchLine,
    line2: adsk.fusion.SketchLine,
    text_point: Vector | adsk.core.Point3D | None = None,
    is_driving: bool = True,
):
    """Add an angle dimension between two lines."""
    if isinstance(text_point, Vector):
        text_point = point3d(text_point)
    return line1.parentSketch.sketchDimensions.addAngularDimension(
        line1,
        line2,
        (
            cast(adsk.core.Point3D, text_point)
            if text_point
            else line1.startSketchPoint.geometry
        ),
        is_driving,
    )
