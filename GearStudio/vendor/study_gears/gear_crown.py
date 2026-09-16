# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from .guard import checkpoint
from math import pi, ceil, asin, sin, cos, tan, sqrt, floor

import adsk.core
import adsk.fusion

from . import gear_curve
from .lib import fusion_helper as fh
from .lib.fusion_helper import Vector
from .lib.function import find_root, minimize
from .lib.spline import interpolate as spline, evenly_spaced_points_on_spline
from .math_crown import calc_tooth_profiles, generate_pinion_tooth






def gear_crown(
    wrapper_occurrence: adsk.fusion.Occurrence,
    params: gear_curve.GearParams,  # transverse parameters for pinion gear
    z: int,  # number of teeth of crown gear
    w1: float,  # outer width
    w2: float,  # inner width
    helix_angle: float,
    base_thickness: float | None = None,
):
    pinion = generate_pinion_tooth(params)

    rp = params.m * params.z / 2  # pinion
    rp2 = params.m * z / 2  # crown gear
    # mk = params.mk * params.m
    mf = params.mf * params.m
    rt = rp + mf + params.shift * params.m  # extended tip circle radius
    tan_beta = tan(helix_angle)
    factor = tan_beta / rp

    def generate_patch(sketch: adsk.fusion.Sketch, profile: list[Vector]):
        # draw the profile on the cylindrical surface
        c1 = fh.sketch_fitted_splines(sketch, profile)
        arc = sketch.sketchCurves.sketchArcs.addByCenterStartEnd(
            fh.point3d(0, 0, c1.endSketchPoint.geometry.z),
            c1.startSketchPoint,
            c1.endSketchPoint,
        )
        fh.sketch_fix_all(sketch)

        # create a patch from the sketch curves making a closed loop
        return fh.comp_patch(gear, arc, fh.FeatureOperations.new_body).bodies[0]

    def generate_donut_body():
        """extrude the donut between inner and outer circles"""
        sketch = gear.sketches.add(gear.xYConstructionPlane)
        sketch = sketch.createForAssemblyContext(gear_occurrence)
        sketch.isComputeDeferred = True
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            fh.point3d(0, 0, -(rp + params.shift * params.m)), rp2 - w2 * params.m
        )
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            fh.point3d(0, 0, -(rp + params.shift * params.m)), rp2 + w1 * params.m
        )
        fh.sketch_fix_all(sketch)
        sketch.isComputeDeferred = False

        return fh.comp_extrude(
            gear,
            sketch.profiles[1],
            fh.FeatureOperations.new_body,
            (params.m * params.mk, params.m * params.mf + (params.m if base_thickness is None else base_thickness)),
        ).bodies[0]

    def draw_reference_circle_and_axis():
        """Draw reference circle and axis of the crown gear.
        Returns the center of the circle."""

        sketch = gear.sketches.add(gear.xYConstructionPlane)
        sketch = sketch.createForAssemblyContext(gear_occurrence)
        sketch.isComputeDeferred = True
        ref = sketch.sketchCurves.sketchCircles.addByCenterRadius(
            fh.point3d(0, 0, -(rp + params.shift * params.m)), rp2
        )
        ref.isConstruction = True
        ref.isFixed = True
        axis = sketch.sketchCurves.sketchLines.addByTwoPoints(
            fh.point3d(0, 0, -(rp + (params.shift - params.mk) * params.m)),
            fh.point3d(0, 0, -(rp + (params.shift + params.mf) * params.m)),
        )
        axis.isConstruction = True
        fh.sketch_fix_all(sketch)
        sketch.isComputeDeferred = False

        return ref.centerSketchPoint

    camera_previous = fh.camera_setup(
        Vector(-rp2, 0, 2 * rp2 - rt),
        Vector(rp2, 0, -rt),
        Vector(0, 0, 1),
        2 * pi / z,
        occurrence=wrapper_occurrence,
    )

    # wrapper component
    wrapper = wrapper_occurrence.component
    gear_occurrence = wrapper.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    gear_occurrence = gear_occurrence.createForAssemblyContext(wrapper_occurrence)
    gear_occurrence.isGroundToParent = False
    gear = gear_occurrence.component

    donut = generate_donut_body()
    center = draw_reference_circle_and_axis()
    fh.comp_built_joint_revolute(wrapper, gear_occurrence, wrapper_occurrence, center)

    sketch1 = gear.sketches.add(gear.xYConstructionPlane)
    sketch1.isComputeDeferred = True
    sketch2 = gear.sketches.add(gear.xYConstructionPlane)
    sketch2.isComputeDeferred = True

    patches: list[tuple[adsk.fusion.BRepBody, adsk.fusion.BRepBody]] = []

    # generate the groove cross sections
    extension = 1.1
    phi_range = extension * (w2 + w1) * params.m * factor * params.z / z
    n = max(ceil((w2 + w1) / 0.5), ceil(phi_range / pi * 180 / 5))
    fh.app_refresh()
    for i in range(0, n + 1):
        checkpoint()
        t = extension * (-w2 + (w2 + w1) * i / n) * params.m
        involute, undercut = calc_tooth_profiles(pinion, params, z, helix_angle, t)
        patches.append((generate_patch(sketch1, involute), generate_patch(sketch2, undercut)))
        fh.app_refresh()

    for sk in [sketch1, sketch2]:
        checkpoint()
        sk.isComputeDeferred = False
        sk.isVisible = False

    # cut the tooth groove from the donut
    loft1 = fh.comp_loft(
        gear, fh.FeatureOperations.new_body, [p[0].faces[0] for p in patches]
    ).bodies[0]
    loft2 = fh.comp_loft(
        gear, fh.FeatureOperations.new_body, [p[1].faces[0] for p in patches]
    ).bodies[0]
    fh.app_refresh()

    # remove the used patches
    fh.comp_remove(gear, [p[0] for p in patches])
    fh.comp_remove(gear, [p[1] for p in patches])

    # create a circular pattern of the tooth groove
    lofts = fh.comp_circular_pattern(gear, [loft1, loft2], gear.zConstructionAxis, z).bodies
    fh.comp_combine(gear, donut, lofts, fh.FeatureOperations.cut)

    fh.camera_setup(camera_previous)

    return gear
