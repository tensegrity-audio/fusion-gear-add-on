# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from .guard import checkpoint
from math import asin, acos, atan, tan, sin, cos, pi, atan2, sqrt, ceil, log
from collections.abc import Iterable
from typing import Literal

import adsk.core, adsk.fusion

from .lib import fusion_helper as fh
from .lib.fusion_helper import Vector
from .lib.function import minimize
from .math_bevel import Params, gear_curves, tooth_groove








def generate_gear(
    wrapper_occurrence: adsk.fusion.Occurrence,
    params: Params,
    axis: Vector,
    z: int,
    groove_shape: list[Iterable[Vector]],
    flip: Literal[1, -1],
    phi: float,
    internal: bool,
    printable: bool = False,
):
    r0 = params.r0
    m = params.m
    mk = params.mk
    mf = params.mf
    rm = params.rm
    r = params.r
    width = params.width
    beta = params.beta

    wrapper = wrapper_occurrence.component
    gear_occurrence = wrapper.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    gear_occurrence = gear_occurrence.createForAssemblyContext(wrapper_occurrence)
    gear_occurrence.isGroundToParent = False
    gear = gear_occurrence.component

    def generate_patch(groove_shape: list[Iterable[Vector]]):
        """generate the patch for the tooth groove shape"""

        def connect_by_splines(sketch: adsk.fusion.Sketch, tooth: list[Iterable[Vector]]):
            """Generate splines and connect them with each other to make a closed loop."""

            result: list[adsk.fusion.SketchFittedSpline] = []
            for i, curve in enumerate(tooth):
                checkpoint()
                points = [fh.point3d(p) for p in curve]
                if len(points) < 2:
                    continue
                if i > 0:
                    points[0] = result[-1].endSketchPoint  # replace the first point
                    if i == len(tooth) - 1:
                        points[-1] = result[0].startSketchPoint  # replace the last point
                result.append(sketch.sketchCurves.sketchFittedSplines.add(fh.collection(points)))
            return result

        sketch1 = gear.sketches.add(gear.xYConstructionPlane)
        sketch1.isComputeDeferred = True
        connect_by_splines(sketch1, groove_shape)
        fh.sketch_fix_all(sketch1)
        sketch1.isComputeDeferred = False

        patch = fh.comp_patch(
            gear,
            sketch1.sketchCurves[0],
            fh.FeatureOperations.new_body,
        ).bodies[0]
        sketch1.isVisible = False
        return patch

    def base_donut_and_axis():
        """generate the base body donut of the gear and rotational axis"""

        r1 = r0
        r2 = r0 - width
        # draw cross section of the donut
        sketch2 = gear.sketches.add(gear.xYConstructionPlane)
        sketch2.isComputeDeferred = True
        # points on the outer side of the donut
        if not internal:
            va = Vector(r0, 0, -mk * m * flip)  # tip
            vb = Vector(r0, 0, (mf + 1) * m * flip)  # bottom - m
        else:
            va = Vector(r0, 0, mk * m * flip)  # tip
            vb = Vector(r0, 0, -(mf + 1) * m * flip)  # bottom - m
        # points on the inner side of the donut
        vas = va * ((r0 - width) / r0)  # scale the tip point
        vbs = vb * ((r0 - width) / r0)  # scale the bottom point
        la = fh.sketch_line(sketch2, va, vb)
        lb = fh.sketch_line(sketch2, vas, vbs)
        fh.sketch_line(sketch2, la.startSketchPoint, lb.startSketchPoint)  # va, vas
        vax0 = axis.normalize(r0 * sqrt(1 - (rm * z / 2) ** 2))
        vax1 = axis.normalize(axis.normalize().dot(vb))  # projected bottom
        vax2 = axis.normalize(axis.normalize().dot(vbs))  # projected bottom scaled
        if not internal:
            lc = fh.sketch_line(sketch2, la.endSketchPoint, vax1)  # vb, vax1
            ld = fh.sketch_line(sketch2, lb.endSketchPoint, vax2)  # vbs,  vax2
            if abs(vax2 - vax1) > abs(vax0 - vax1):
                le = fh.sketch_line(sketch2, lc.endSketchPoint, ld.endSketchPoint)  # vax1, vax2
            else:
                le = fh.sketch_line(sketch2, lc.endSketchPoint, vax0)  # vax1, vax0
                sketch2.geometricConstraints.addCoincident(ld.endSketchPoint, le)
            fh.sketch_fix_all(sketch2)
            if printable and abs((va - vb).normalize().dot(axis.normalize())) < 1 / sqrt(2):
                # too shallow side wall was detected
                la.isConstruction = True
                lf = fh.sketch_line(sketch2, la.endSketchPoint, vax1 + (vb - vax1) * 1.01)
                sketch2.geometricConstraints.addCoincident(lf.endSketchPoint, lc)
                lg = fh.sketch_line(sketch2, lf.endSketchPoint, la.startSketchPoint)
                sketch2.sketchDimensions.addAngularDimension(
                    le, lg, fh.point3d((va + vbs) / 2)
                ).value = pi / 4
                r1 = lf.endSketchPoint.geometry.distanceTo(fh.point3d())
        else:
            lc = fh.sketch_line(sketch2, la.endSketchPoint, lb.endSketchPoint)  # vb, vbs
            if abs(vax1 - vax2) > abs(vax0 - vax2):
                le = fh.sketch_line(sketch2, vax2, vax1)
            else:
                le = fh.sketch_line(sketch2, vax2, vax0)
            vc = Vector(r0, 0, -mf * m * flip)  # tooth bottom
            vcs = vc * ((r0 - width) / r0)  # scale vc
            lh = fh.sketch_line(sketch2, vc, vcs)
            fh.sketch_fix_all(sketch2)

            if printable:
                if abs((vbs - vb).normalize().dot(axis.normalize())) < 1 / sqrt(2):
                    # too shallow outer wall was detected
                    lc.isConstruction = True
                    ld = fh.sketch_line(sketch2, lb.endSketchPoint, vbs + (vbs - vax2) * 0.01)
                    sketch2.geometricConstraints.addPerpendicular(ld, le)
                    lf = fh.sketch_line(sketch2, ld.endSketchPoint, la.endSketchPoint)
                    sketch2.sketchDimensions.addAngularDimension(le, lf, fh.point3d(va)).value = (
                        pi / 4
                    )
                if abs((vbs - vas).normalize().dot(axis.normalize())) < 1 / sqrt(2):
                    # too shallow inner wall was detected
                    lb.isConstruction = True
                    ld = fh.sketch_line(sketch2, lb.endSketchPoint, vbs - (vbs - vax2) * 0.01)
                    sketch2.geometricConstraints.addPerpendicular(ld, le)
                    lf = fh.sketch_line(sketch2, ld.endSketchPoint, lb.startSketchPoint)
                    sketch2.sketchDimensions.addAngularDimension(
                        le, lf, fh.point3d((vbs + vax2) / 3)
                    ).value = (pi / 4)
                    lg = fh.sketch_line(sketch2, lh.endSketchPoint, vcs-(vcs-vc)*0.1)
                    sketch2.geometricConstraints.addCoincident(lg.endSketchPoint, ld)
                    r2 = lg.endSketchPoint.geometry.distanceTo(fh.point3d())

        sketch2.isComputeDeferred = False

        # create the donut by revolving the sketch around the axis
        donut = fh.comp_revolve(
            gear,
            sketch2.profiles,
            le,
            fh.FeatureOperations.new_body,
        ).bodies[0]

        donut2 = None
        if internal:  # thinner donut upto tooth bottom
            donut2 = fh.comp_revolve(
                gear,
                sketch2.profiles[0],
                le,
                fh.FeatureOperations.new_body,
            ).bodies[0]

        # construct plane for sketch to show the reference circle and axis of the gear
        distance = abs(Vector(le.startSketchPoint.geometry) - vax0)
        length = le.startSketchPoint.geometry.distanceTo(le.endSketchPoint.geometry)
        inp = gear.constructionPlanes.createInput(gear_occurrence)
        inp.setByDistanceOnPath(le, fh.value_input(distance / length))
        plane = gear.constructionPlanes.add(inp)

        # draw the reference circle and axis of the gear
        sketch3 = gear.sketches.add(plane)
        sketch3.isComputeDeferred = True
        reference_circle = sketch3.sketchCurves.sketchCircles.addByCenterRadius(
            fh.point3d(), r0 * rm * z / 2
        )
        reference_circle.isConstruction = True
        ax = sketch3.sketchCurves.sketchLines.addByTwoPoints(
            fh.point3d(z=-distance),
            fh.point3d(z=max(0, length - distance)),
        )
        ax.isConstruction = True
        fh.sketch_fix_all(sketch3)
        sketch3.isComputeDeferred = False

        return donut, donut2, ax.createForAssemblyContext(gear_occurrence), r1, r2

    def duplicate_and_loft(
        patch: adsk.fusion.BRepBody,
        axis_line: adsk.fusion.SketchLine,
        donut: adsk.fusion.BRepBody,
        operation: int,
    ):
        def spiral_angle(scale: float):
            return flip * 2 * r * tan(beta) / z * log(scale)

        # determine the lofting range of the tooth groove shape
        extension = 1.02
        scale_start = r1 / r0 * extension
        scale_end = r2 / r0 / extension
        scale_n = 1 if beta == 0 else max(5, ceil(abs(spiral_angle(scale_end)) / pi * 40))

        # create the tooth patches for lofting by scaling and rotating the original patch
        patches: list[adsk.fusion.BRepBody] = []
        for i in range(scale_n + 1):
            checkpoint()
            scale = scale_start * (scale_end / scale_start) ** (i / scale_n)
            copy = fh.comp_copy(gear, patch)
            fh.comp_scale(gear, copy.bodies[0], gear.originConstructionPoint, scale)
            if (scale - 1) * tan(beta) != 0:
                fh.comp_move_rotate(gear, copy.bodies[0], axis_line, spiral_angle(scale))
            patches.append(copy.bodies[0])
        fh.comp_remove(gear, patch)  # remove the original

        # loft the patches to create the tooth shape and circular pattern it
        tooth = fh.comp_loft(gear, operation, [p.faces[0] for p in patches], donut)
        fh.comp_remove(gear, patches)
        return tooth

    # generate the gear by cutting the donut with the tooth groove shape
    patch = generate_patch(groove_shape)
    donut, donut2, axis_line, r1, r2 = base_donut_and_axis()
    fh.app_refresh()

    op = adsk.fusion.FeatureOperations.CutFeatureOperation
    if internal:
        op = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    profile = duplicate_and_loft(patch, axis_line, donut, op)
    fh.app_refresh()

    if not internal:
        # circular pattern the groove cutting
        gear_body = fh.comp_circular_pattern(gear, profile, axis_line, z).bodies[0]
    else:
        fh.app_refresh()
        # circular pattern the teeth and combine them to base donut
        teeth = fh.comp_circular_pattern(gear, profile.bodies[0], axis_line, z).bodies
        gear_body = fh.comp_combine(gear, donut2, teeth, fh.FeatureOperations.join).bodies[0]
        fh.app_refresh()

    if phi != 0:
        if z % 2 == 1:  # adjust phase of the gear
            fh.comp_move_rotate(gear, gear_body, axis_line, pi / z)
        # rotate the gear for meshing the internal gear
        gear_occurrence.transform2 = fh.matrix_rotate(
            phi, fh.vector3d(0, 1, 0), base=gear_occurrence.transform2
        )
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.snapshots.add()  # capture the position

    fh.app_refresh()

    # generate joint between the gear and wrapper
    # This code does not work correctly for the internal gear at this moment.
    # Somehow, the axis_line before transformation is referred
    # even after design.snapshots.add() call.
    # Replacing `axis_line` with `axis_line.nativeObject.createForAssemblyContext(gear_occurrence)`
    # did not help.
    fh.comp_built_joint_revolute(
        wrapper,
        gear_occurrence,
        wrapper_occurrence,
        axis_line,
        point_type=adsk.fusion.JointKeyPointTypes.EndKeyPoint,
    )

    return gear_occurrence
