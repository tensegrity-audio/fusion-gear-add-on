# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from .guard import checkpoint
from collections.abc import Callable
from copy import copy
from dataclasses import dataclass
from functools import reduce
from math import pi, cos, asin, atan, tan, floor, ceil

import adsk.core, adsk.fusion

from .lib.function import minimize, find_root

from . import gear_curve
from .lib import fusion_helper as fh
from .lib.fusion_helper import Vector, vec, radius_from_3points
from .gear_worm_wheel_segment import Line, Arc, Segments
from .lib.spline import evenly_spaced_points_on_spline, interpolate
from .math_worm_wheel import worm_wheel_shape_at_height


def gear_worm_wheel(
    parent_occurrence: adsk.fusion.Occurrence,
    params: gear_curve.GearParams,
    worm_diameter: float,
    worm_spirals: int,
    thickness: float,
    helix_angle: float,
):
    parent = parent_occurrence.component
    occurrence = parent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occurrence = occurrence.createForAssemblyContext(parent_occurrence)
    occurrence.isGroundToParent = False
    comp = occurrence.component

    rk = params.m / cos(helix_angle) * params.z / 2 + params.m * (params.mk + params.shift)
    camera_backup = fh.camera_setup(
        Vector(x=rk + max(thickness, pi * params.m) * 4),
        Vector(),
        Vector(z=1),
        perspective=pi / 8,
        occurrence=occurrence,
    )

    sketch = comp.sketches.add(comp.xYConstructionPlane)
    sketch = sketch.createForAssemblyContext(occurrence)
    sketch.isComputeDeferred = True

    # generate the groove profiles for height z
    n = max(4, ceil(thickness / params.m / cos(helix_angle) * 1.5))
    for i in range(n):
        checkpoint()
        z = (n - 1 - i) / (n - 1) * thickness * 1.005 / 2
        shape = worm_wheel_shape_at_height(z, params, helix_angle, worm_diameter / 2, worm_spirals)
        if len(shape) == 0:
            continue
        shape = evenly_spaced_points_on_spline(shape, 50)
        spline = fh.sketch_fitted_splines(sketch, [Vector(v.x, v.y, z) for v in shape])
        sketch.sketchCurves.sketchArcs.addByCenterStartEnd(
            fh.point3d(0, 0, z),
            spline.endSketchPoint,
            spline.startSketchPoint,
        )
        fh.app_refresh()
    fh.sketch_fix_all(sketch)
    sketch.isComputeDeferred = False

    # generate patch
    # We generate the patch from curve because generating patch from profile sometimes fails.
    curves = sorted(sketch.sketchCurves, key=lambda c: c.boundingBox.minPoint.z)
    patches = [
        fh.comp_patch(comp, curves[i * 2 : (i + 1) * 2], fh.FeatureOperations.new_body).bodies[0]
        for i in range(1, floor(len(curves) / 2))
    ]
    sketch.isVisible = False

    # copy it to the other side with rotation
    for i, patch in enumerate(patches.copy()):
        checkpoint()
        if patch.boundingBox.minPoint.z > 0:
            patch2 = fh.comp_mirror(comp, patch, comp.xZConstructionPlane).bodies[0]
            fh.comp_move_free(
                comp,
                patch2,
                fh.matrix_translate(z=-patch.boundingBox.minPoint.z * 2),
            )
            patches.insert(0, patch2)

    # create a disk by extruding the tip circle
    sketch2 = comp.sketches.add(comp.xYConstructionPlane)
    sketch2.sketchCurves.sketchCircles.addByCenterRadius(fh.point3d(), rk)
    disk = fh.comp_extrude(
        comp,
        sketch2.profiles[0],
        fh.FeatureOperations.new_body,
        thickness,
        True,
        True,
    )

    # cut a groove
    teeth = fh.comp_loft(
        comp,
        fh.FeatureOperations.cut,
        [p.faces[0] for p in patches],
        disk.bodies[0],
    )
    fh.comp_remove(comp, patches)

    # copy it around the axis
    fh.comp_circular_pattern(comp, teeth, comp.zConstructionAxis, round(params.z))

    # draw axis
    sketch3 = comp.sketches.add(comp.xYConstructionPlane)
    center_axis = sketch3.sketchCurves.sketchLines.addByTwoPoints(
        fh.point3d(z=-thickness / 2), fh.point3d(z=thickness / 2)
    )
    center_axis.isFixed = True

    # draw reference circle
    rp = params.m / cos(helix_angle) * params.z / 2
    circle = sketch3.sketchCurves.sketchCircles.addByCenterRadius(fh.point3d(), rp)
    circle.isConstruction = True
    sketch3.sketchDimensions.addDiameterDimension(circle, fh.point3d(rp, rp), isDriving=True)
    for p in sketch3.sketchPoints:
        checkpoint()
        p.isFixed = True

    fh.camera_setup(camera_backup)
