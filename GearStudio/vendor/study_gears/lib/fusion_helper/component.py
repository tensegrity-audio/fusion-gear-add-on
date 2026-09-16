# Vendored from Osamu Takeuchi, MIT. See LICENSE.txt and UPSTREAM.md.
from __future__ import annotations
from ...guard import checkpoint
import math
from collections.abc import Callable, Iterable
from typing import cast

import adsk.core, adsk.fusion

from .helpers import collection, value_input


def comp_built_joint_revolute(
    comp: adsk.fusion.Component,
    occ1: adsk.fusion.Occurrence,
    occ2: adsk.fusion.Occurrence,
    obj: (
        adsk.fusion.SketchPoint
        | adsk.fusion.ConstructionPoint
        | adsk.fusion.BRepVertex
        | adsk.fusion.BRepFace
        | adsk.fusion.Profile
        | adsk.fusion.BRepEdge
        | adsk.fusion.SketchCurve
    ),
    direction_or_axis_with_context: (
        int | adsk.fusion.JointDirections | adsk.core.Base
    ) = cast(
        adsk.fusion.JointDirections, adsk.fusion.JointDirections.ZAxisJointDirection
    ),
    point_type: adsk.fusion.JointKeyPointTypes | int | None = None,
):
    checkpoint(force=True)
    if isinstance(obj, adsk.fusion.BRepFace):
        geo = adsk.fusion.JointGeometry.createByPlanarFace(
            obj,
            cast(adsk.fusion.BRepEdge, None),
            (
                cast(
                    adsk.fusion.JointKeyPointTypes,
                    adsk.fusion.JointKeyPointTypes.CenterKeyPoint,
                )
                if point_type is None
                else cast(adsk.fusion.JointKeyPointTypes, point_type)
            ),
        )
    elif isinstance(obj, adsk.fusion.Profile):
        geo = adsk.fusion.JointGeometry.createByProfile(
            obj,
            cast(adsk.fusion.SketchCurve, None),
            (
                cast(
                    adsk.fusion.JointKeyPointTypes,
                    adsk.fusion.JointKeyPointTypes.CenterKeyPoint,
                )
                if point_type is None
                else cast(adsk.fusion.JointKeyPointTypes, point_type)
            ),
        )
    elif isinstance(obj, adsk.fusion.SketchCurve) or isinstance(
        obj, adsk.fusion.BRepEdge
    ):
        geo = adsk.fusion.JointGeometry.createByCurve(
            obj,
            (
                cast(
                    adsk.fusion.JointKeyPointTypes,
                    adsk.fusion.JointKeyPointTypes.StartKeyPoint,
                )
                if point_type is None
                else cast(adsk.fusion.JointKeyPointTypes, point_type)
            ),
        )
    else:
        geo = adsk.fusion.JointGeometry.createByPoint(obj)
    inp = comp.asBuiltJoints.createInput(occ1, occ2, geo)
    if isinstance(direction_or_axis_with_context, int) or isinstance(
        direction_or_axis_with_context, adsk.fusion.JointDirections
    ):
        inp.setAsRevoluteJointMotion(
            cast(adsk.fusion.JointDirections, direction_or_axis_with_context)
        )
    else:
        inp.setAsRevoluteJointMotion(
            cast(
                adsk.fusion.JointDirections,
                adsk.fusion.JointDirections.CustomJointDirection,
            ),
            direction_or_axis_with_context,
        )
    return comp.asBuiltJoints.add(inp)


def comp_built_joint_revolute2(
    comp: adsk.fusion.Component,
    occ1: adsk.fusion.Occurrence,
    occ2: adsk.fusion.Occurrence,
    face: adsk.fusion.BRepFace,
    direction_or_axis_with_context: int | adsk.fusion.JointDirections | adsk.core.Base,
):
    checkpoint(force=True)
    geo = adsk.fusion.JointGeometry.createByPlanarFace(
        face,
        cast(adsk.fusion.BRepEdge, None),
        cast(
            adsk.fusion.JointKeyPointTypes,
            adsk.fusion.JointKeyPointTypes.CenterKeyPoint,
        ),
    )
    inp = comp.asBuiltJoints.createInput(occ1, occ2, geo)
    if isinstance(direction_or_axis_with_context, int) or isinstance(
        direction_or_axis_with_context, adsk.fusion.JointDirections
    ):
        inp.setAsRevoluteJointMotion(
            cast(adsk.fusion.JointDirections, direction_or_axis_with_context)
        )
    else:
        inp.setAsRevoluteJointMotion(
            cast(
                adsk.fusion.JointDirections,
                adsk.fusion.JointDirections.CustomJointDirection,
            ),
            direction_or_axis_with_context,
        )
    return comp.asBuiltJoints.add(inp)


def comp_joint_revolute(
    comp: adsk.fusion.Component,
    p1: adsk.core.Base,
    p2: adsk.core.Base,
    direction_or_axis_with_context: int | adsk.fusion.JointDirections | adsk.core.Base,
):
    checkpoint(force=True)
    joint1 = adsk.fusion.JointGeometry.createByPoint(p1)
    joint2 = adsk.fusion.JointGeometry.createByPoint(p2)
    inp = comp.joints.createInput(joint1, joint2)
    if isinstance(direction_or_axis_with_context, int) or isinstance(
        direction_or_axis_with_context, adsk.fusion.JointDirections
    ):
        inp.setAsRevoluteJointMotion(
            cast(adsk.fusion.JointDirections, direction_or_axis_with_context)
        )
    else:
        inp.setAsRevoluteJointMotion(
            cast(
                adsk.fusion.JointDirections,
                adsk.fusion.JointDirections.CustomJointDirection,
            ),
            direction_or_axis_with_context,
        )
    return comp.joints.add(inp)


def comp_joint_slider(
    comp: adsk.fusion.Component,
    p1: adsk.core.Base,
    p2: adsk.core.Base,
    direction_or_axis_with_context: int | adsk.core.Base,
):
    checkpoint(force=True)
    joint1 = adsk.fusion.JointGeometry.createByPoint(p1)
    joint2 = adsk.fusion.JointGeometry.createByPoint(p2)
    inp = comp.joints.createInput(joint1, joint2)
    if isinstance(direction_or_axis_with_context, int) or isinstance(
        direction_or_axis_with_context, adsk.fusion.JointDirections
    ):
        inp.setAsSliderJointMotion(
            cast(adsk.fusion.JointDirections, direction_or_axis_with_context)
        )
    else:
        inp.setAsSliderJointMotion(
            cast(
                adsk.fusion.JointDirections,
                adsk.fusion.JointDirections.CustomJointDirection,
            ),
            direction_or_axis_with_context,
        )
    return comp.joints.add(inp)


def comp_remove(
    comp: adsk.fusion.Component,
    entities: adsk.core.Base | Iterable[adsk.core.Base],
):
    checkpoint(force=True)
    if not isinstance(entities, Iterable):
        entities = [entities]
    return [comp.features.removeFeatures.add(m) for m in entities]


def comp_loft(
    comp: adsk.fusion.Component,
    operation: adsk.fusion.FeatureOperations | int,
    entities: list[adsk.core.Base],
    participants: adsk.fusion.BRepBody | Iterable[adsk.fusion.BRepBody] | None = None,
    merge_tangent: bool = False,
):
    checkpoint(force=True)
    inp = comp.features.loftFeatures.createInput(
        cast(adsk.fusion.FeatureOperations, operation)
    )
    for m in entities:
        checkpoint()
        inp.loftSections.add(m)
    if participants is not None:
        if isinstance(participants, Iterable):
            participants = list(participants)
        else:
            participants = [participants]
        inp.participantBodies = participants
    inp.isTangentEdgesMerged = merge_tangent
    return comp.features.loftFeatures.add(inp)


def comp_rectangular_pattern(
    comp: adsk.fusion.Component,
    entities: adsk.core.Base | Iterable[adsk.core.Base],
    axis: adsk.core.Base | tuple[adsk.core.Base, adsk.core.Base],
    quantity: int | tuple[int, int],
    distance: float | str | tuple[float | str, float | str],
    is_spacing: bool,
    symmetric: bool = False,
    compute: (
        adsk.fusion.PatternComputeOptions | int
    ) = adsk.fusion.PatternComputeOptions.IdenticalPatternCompute,
):
    checkpoint(force=True)
    inp = comp.features.rectangularPatternFeatures.createInput(
        collection(entities),
        axis if not isinstance(axis, tuple) else axis[0],
        (
            value_input(quantity)
            if not isinstance(quantity, tuple)
            else value_input(quantity[0])
        ),
        (
            value_input(distance)
            if not isinstance(distance, tuple)
            else value_input(distance[0])
        ),
        cast(
            adsk.fusion.PatternDistanceType,
            (
                adsk.fusion.PatternDistanceType.SpacingPatternDistanceType
                if is_spacing
                else adsk.fusion.PatternDistanceType.ExtentPatternDistanceType
            ),
        ),
    )
    if symmetric:
        inp.isSymmetricInDirectionOne = True
    if isinstance(axis, tuple):

        if not isinstance(quantity, tuple):
            quantity = (quantity, quantity)
        if not isinstance(distance, tuple):
            distance = (distance, distance)
        inp.setDirectionTwo(axis[1], value_input(quantity[1]), value_input(distance[1]))
        if symmetric:
            inp.isSymmetricInDirectionTwo = True
    else:
        inp.quantityTwo = value_input(1)
    inp.patternComputeOption = cast(adsk.fusion.PatternComputeOptions, compute)
    return comp.features.rectangularPatternFeatures.add(inp)


def comp_move_free(
    comp: adsk.fusion.Component,
    entities: adsk.core.Base | Iterable[adsk.core.Base],
    matrixes: adsk.core.Matrix3D | Iterable[adsk.core.Matrix3D],
    occurrence: adsk.fusion.Occurrence | None = None,
):
    checkpoint(force=True)
    if not isinstance(matrixes, Iterable):
        matrixes = [matrixes]
    if occurrence is not None:
        (trans_inv := occurrence.transform2.copy()).invert()
        matrixes = [trans_inv, *matrixes, occurrence.transform2]
    matrix = adsk.core.Matrix3D.create()
    for m in matrixes:
        checkpoint()
        matrix.transformBy(m)
    if matrix.isEqualTo(adsk.core.Matrix3D.create()):
        return None
    inp = comp.features.moveFeatures.createInput2(
        collection(entities),
    )
    inp.defineAsFreeMove(matrix)
    return comp.features.moveFeatures.add(inp)


def comp_move_rotate(
    comp: adsk.fusion.Component,
    entities: adsk.core.Base | Iterable[adsk.core.Base],
    axis: adsk.core.Base,
    angle: float | str,
):
    checkpoint(force=True)
    """Rotate entities around axis. The axis must have its
    AssemblyContext fully upto to the root component."""
    inp = comp.features.moveFeatures.createInput2(
        collection(entities),
    )
    inp.defineAsRotate(axis, value_input(angle))
    return comp.features.moveFeatures.add(inp)


def comp_split_body(
    comp: adsk.fusion.Component,
    split_bodies: adsk.core.Base | Iterable[adsk.core.Base],
    splitting_tool: adsk.core.Base,
    extend_tool: bool,
):
    checkpoint(force=True)
    inp = comp.features.splitBodyFeatures.createInput(
        collection(split_bodies),
        splitting_tool,
        extend_tool,
    )
    return comp.features.splitBodyFeatures.add(inp)


def comp_patch(
    comp: adsk.fusion.Component,
    profiles: (
        adsk.fusion.Profile
        | Iterable[adsk.fusion.Profile]
        | adsk.fusion.SketchCurve
        | Iterable[adsk.fusion.SketchCurve]
        | adsk.fusion.BRepEdge
    ),
    operation: adsk.fusion.FeatureOperations | int,
):
    checkpoint(force=True)
    if isinstance(profiles, adsk.fusion.SketchCurve) or isinstance(
        profiles, adsk.fusion.BRepEdge
    ):
        inp = comp.features.patchFeatures.createInput(
            profiles,
            cast(adsk.fusion.FeatureOperations, operation),
        )
    else:
        inp = comp.features.patchFeatures.createInput(
            collection(profiles),
            cast(adsk.fusion.FeatureOperations, operation),
        )
    return comp.features.patchFeatures.add(inp)


def comp_scale(
    comp: adsk.fusion.Component,
    entities: adsk.core.Base | Iterable[adsk.core.Base],
    center: (
        adsk.fusion.BRepVertex | adsk.fusion.SketchPoint | adsk.fusion.ConstructionPoint
    ),
    scale: float | tuple[float, float, float],
):
    checkpoint(force=True)
    inp = comp.features.scaleFeatures.createInput(
        collection(entities),
        center,
        value_input(scale) if isinstance(scale, float) else value_input(1),
    )
    if isinstance(scale, tuple):
        inp.setToNonUniform(*[value_input(s) for s in scale])
    return comp.features.scaleFeatures.add(inp)


def comp_mirror(
    comp: adsk.fusion.Component,
    entities: adsk.core.Base | Iterable[adsk.core.Base],
    plane: adsk.core.Base,
    combine: bool = False,
    compute: (
        adsk.fusion.PatternComputeOptions | int
    ) = adsk.fusion.PatternComputeOptions.IdenticalPatternCompute,
):
    checkpoint(force=True)
    inp = comp.features.mirrorFeatures.createInput(
        collection(entities),
        plane,
    )
    inp.isCombine = combine
    inp.patternComputeOption = cast(adsk.fusion.PatternComputeOptions, compute)
    return comp.features.mirrorFeatures.add(inp)


def comp_revolve(
    comp: adsk.fusion.Component,
    profile: adsk.core.Base | Iterable[adsk.core.Base],
    axis: adsk.core.Base,
    operation: adsk.fusion.FeatureOperations | int,
    participants: adsk.fusion.BRepBody | Iterable[adsk.fusion.BRepBody] | None = None,
    angle: float | str = 2 * math.pi,
    is_symmetric: bool = False,
    is_solid: bool = True,
):
    checkpoint(force=True)
    inp = comp.features.revolveFeatures.createInput(
        collection(profile), axis, cast(adsk.fusion.FeatureOperations, operation)
    )
    inp.setAngleExtent(is_symmetric, value_input(angle))
    inp.isSolid = is_solid
    if participants is not None:
        if isinstance(participants, adsk.fusion.BRepBody):
            participants = [participants]
        inp.participantBodies = list(participants)
    return comp.features.revolveFeatures.add(inp)


def comp_copy(
    comp: adsk.fusion.Component,
    entities: adsk.core.Base | Iterable[adsk.core.Base],
):
    checkpoint(force=True)
    return comp.features.copyPasteBodies.add(collection(entities))


def distance_extent(
    distance: float | str = 1,
    symmetric: bool = False,
    full_length: bool = False,
    through_all: bool = False,
):
    """create ExtentDefinition"""
    if through_all:
        return adsk.fusion.ThroughAllExtentDefinition.create()
    if symmetric:
        return adsk.fusion.SymmetricExtentDefinition.create(
            value_input(distance), full_length
        )
    return adsk.fusion.DistanceExtentDefinition.create(value_input(distance))


def comp_extrude(
    comp: adsk.fusion.Component,
    profiles: adsk.core.Base | Iterable[adsk.core.Base],
    operation: adsk.fusion.FeatureOperations | int,
    distance: float | str | tuple[float | str, float | str],
    symmetric: bool | tuple[bool, bool] = False,
    full_length: bool | tuple[bool, bool] = False,
    taper_angle: float | str | tuple[float | str, float | str] = 0,
    participants: adsk.fusion.BRepBody | Iterable[adsk.fusion.BRepBody] | None = None,
    solid: bool = True,
    through_all: bool | tuple[bool, bool] = False,
    negative_direction: bool = False,
    offset: float | str = 0,
    thin_extrude_thickness: float | str | tuple[float | str, float | str] = 0,
    thin_extrude_wall_location: (
        adsk.fusion.ThinExtrudeWallLocation
        | tuple[
            adsk.fusion.ThinExtrudeWallLocation, adsk.fusion.ThinExtrudeWallLocation
        ]
        | int
        | tuple[int, int]
    ) = cast(
        adsk.fusion.ThinExtrudeWallLocation, adsk.fusion.ThinExtrudeWallLocation.Side1
    ),
):
    checkpoint(force=True)
    profiles = [
        p if not isinstance(p, adsk.fusion.SketchCurve) else comp.createOpenProfile(p)
        for p in collection(profiles)
    ]
    inp = comp.features.extrudeFeatures.createInput(
        collection(profiles), cast(adsk.fusion.FeatureOperations, operation)
    )
    inp.startExtent = adsk.fusion.OffsetStartDefinition.create(value_input(offset))
    thin_extrude = thin_extrude_thickness != 0
    inp.isThinExtrude = thin_extrude
    if isinstance(distance, tuple):
        if not isinstance(taper_angle, tuple):
            taper_angle = (taper_angle, taper_angle)
        if not isinstance(symmetric, tuple):
            symmetric = (symmetric, symmetric)
        if not isinstance(full_length, tuple):
            full_length = (full_length, full_length)
        if not isinstance(through_all, tuple):
            through_all = (through_all, through_all)
        if not isinstance(thin_extrude_thickness, tuple):
            thin_extrude_thickness = (thin_extrude_thickness, thin_extrude_thickness)
        if not isinstance(thin_extrude_wall_location, tuple):
            thin_extrude_wall_location = (
                cast(adsk.fusion.ThinExtrudeWallLocation, thin_extrude_wall_location),
                cast(adsk.fusion.ThinExtrudeWallLocation, thin_extrude_wall_location),
            )
        extent1 = distance_extent(
            distance[0], symmetric[0], full_length[0], through_all[0]
        )
        extent2 = distance_extent(
            distance[1], symmetric[1], full_length[1], through_all[1]
        )
        if thin_extrude:
            inp.thinExtrudeWallLocationOne = cast(
                adsk.fusion.ThinExtrudeWallLocation, thin_extrude_wall_location[0]
            )
            inp.thinExtrudeWallLocationTwo = cast(
                adsk.fusion.ThinExtrudeWallLocation, thin_extrude_wall_location[1]
            )
            inp.thinExtrudeWallThicknessOne = value_input(thin_extrude_thickness[0])
            inp.thinExtrudeWallThicknessTwo = value_input(thin_extrude_thickness[1])
        adsk.fusion.ThroughAllExtentDefinition.create()
        cast(
            Callable[
                [
                    adsk.fusion.ExtentDefinition,
                    adsk.fusion.ExtentDefinition,
                    adsk.core.ValueInput | None,
                    adsk.core.ValueInput | None,
                ],
                bool,
            ],
            inp.setTwoSidesExtent,
        )(
            extent1,
            extent2,
            value_input(taper_angle[0]) if taper_angle[0] != 0 else None,
            value_input(taper_angle[1]) if taper_angle[1] != 0 else None,
        )
    else:
        if isinstance(taper_angle, tuple):
            taper_angle = taper_angle[0]
        if isinstance(symmetric, tuple):
            symmetric = symmetric[0]
        if isinstance(full_length, tuple):
            full_length = full_length[0]
        if isinstance(through_all, tuple):
            through_all = through_all[0]
        if isinstance(thin_extrude_thickness, tuple):
            thin_extrude_thickness = thin_extrude_thickness[0]
        if isinstance(thin_extrude_wall_location, tuple):
            thin_extrude_wall_location = thin_extrude_wall_location[0]
        if thin_extrude:
            inp.thinExtrudeWallLocationOne = cast(
                adsk.fusion.ThinExtrudeWallLocation, thin_extrude_wall_location
            )
            inp.thinExtrudeWallThicknessOne = value_input(thin_extrude_thickness)
        extent1 = distance_extent(distance, symmetric, full_length, through_all)
        direction = (
            adsk.fusion.ExtentDirections.NegativeExtentDirection
            if negative_direction
            else adsk.fusion.ExtentDirections.PositiveExtentDirection
        )
        cast(
            Callable[
                [
                    adsk.fusion.ExtentDefinition,
                    adsk.fusion.ExtentDirections | int,
                    adsk.core.ValueInput | None,
                ],
                bool,
            ],
            inp.setOneSideExtent,
        )(extent1, direction, value_input(taper_angle) if taper_angle != 0 else None)
    inp.isSolid = solid
    if participants is not None:
        if not isinstance(participants, Iterable):
            participants = [participants]
        inp.participantBodies = list(participants)
    return comp.features.extrudeFeatures.add(inp)


def comp_sweep(
    comp: adsk.fusion.Component,
    profile: adsk.fusion.Profile | Iterable[adsk.fusion.Profile],
    path: adsk.core.Base,
    operation: adsk.fusion.FeatureOperations | int,
    twist: float | str = 0,
    participants: adsk.fusion.BRepBody | Iterable[adsk.fusion.BRepBody] | None = None,
    taper: float | str = 0,
    partial: float | str = 1.0,
    partial2: float | str = 1.0,
    flip: bool = False,
    orientation: adsk.fusion.SweepOrientationTypes | int | None = None,
):
    checkpoint(force=True)
    if not isinstance(path, adsk.fusion.Path):
        path = comp.features.createPath(path)
    inp = comp.features.sweepFeatures.createInput(
        collection(profile), path, cast(adsk.fusion.FeatureOperations, operation)
    )
    inp.twistAngle = value_input(twist)
    if participants is not None:
        if not isinstance(participants, Iterable):
            participants = [participants]
        inp.participantBodies = list(participants)
    inp.taperAngle = value_input(taper)
    inp.isDirectionFlipped = flip
    inp.distanceOne = value_input(partial)
    inp.distanceTwo = value_input(partial2)
    if orientation is not None:
        inp.orientation = cast(adsk.fusion.SweepOrientationTypes, orientation)
    return comp.features.sweepFeatures.add(inp)


def comp_combine(
    comp: adsk.fusion.Component,
    target_body: adsk.fusion.BRepBody,
    tool_bodies: adsk.fusion.BRepBody | Iterable[adsk.fusion.BRepBody],
    operation: adsk.fusion.FeatureOperations | int,
    keep_tools: bool = False,
):
    checkpoint(force=True)
    inp = comp.features.combineFeatures.createInput(
        target_body, collection(tool_bodies)
    )
    inp.operation = cast(adsk.fusion.FeatureOperations, operation)
    inp.isKeepToolBodies = keep_tools
    return comp.features.combineFeatures.add(inp)


def comp_circular_pattern(
    comp: adsk.fusion.Component,
    entities: adsk.core.Base | Iterable[adsk.core.Base],
    axis: adsk.core.Base,
    quantity: int,
    total_angle: float | str = 2 * math.pi,
    symmetric: bool = False,
    compute: (
        adsk.fusion.PatternComputeOptions | int
    ) = adsk.fusion.PatternComputeOptions.IdenticalPatternCompute,
):
    checkpoint(force=True)
    inp = comp.features.circularPatternFeatures.createInput(collection(entities), axis)
    inp.quantity = value_input(quantity)
    inp.totalAngle = value_input(total_angle)
    if symmetric:
        inp.isSymmetric = True
    inp.patternComputeOption = cast(adsk.fusion.PatternComputeOptions, compute)
    return comp.features.circularPatternFeatures.add(inp)


class FeatureOperations:
    join = cast(
        adsk.fusion.FeatureOperations,
        adsk.fusion.FeatureOperations.JoinFeatureOperation,
    )
    cut = cast(
        adsk.fusion.FeatureOperations, adsk.fusion.FeatureOperations.CutFeatureOperation
    )
    intersect = cast(
        adsk.fusion.FeatureOperations,
        adsk.fusion.FeatureOperations.IntersectFeatureOperation,
    )
    new_body = cast(
        adsk.fusion.FeatureOperations,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
    )
    new_component = cast(
        adsk.fusion.FeatureOperations,
        adsk.fusion.FeatureOperations.NewComponentFeatureOperation,
    )

    def __init__(self):
        pass


class ThinExtrudeWallLocation:
    center = cast(
        adsk.fusion.ThinExtrudeWallLocation, adsk.fusion.ThinExtrudeWallLocation.Center
    )
    side1 = cast(
        adsk.fusion.ThinExtrudeWallLocation, adsk.fusion.ThinExtrudeWallLocation.Side1
    )
    side2 = cast(
        adsk.fusion.ThinExtrudeWallLocation, adsk.fusion.ThinExtrudeWallLocation.Side2
    )


def comp_construct_plane_by_offset(
    comp: adsk.fusion.Component,
    plane: adsk.core.Base,
    offset: float | str | adsk.core.ValueInput,
    occurrence_of_plane: adsk.fusion.Occurrence | None = None,
):
    checkpoint(force=True)
    inp = comp.constructionPlanes.createInput(
        cast(adsk.fusion.Occurrence, occurrence_of_plane)
    )
    inp.setByOffset(plane, value_input(offset))
    return comp.constructionPlanes.add(inp)
