"""Native construction commits. Must run inside a Fusion command.execute event.

The controller MUST set executeFailed on every exception to abort Fusion's
transaction, including changes/deletions of native features. Unlike a temporary
B-rep, native feature dependencies cannot be restored by copying a body back.
"""
from copy import deepcopy
import math
import uuid

from . import document as doc
from .builder import generate_native, _verify_solid
from ..vendor.study_gears.guard import bounded
from ..vendor.study_gears.sketch_constraints import DIAMETER_INPUT

GENERATION = "construction_generation"


def require_component_design(design):
    doc._check_design(design)
    _, fusion = doc._api()
    intents = getattr(fusion, "DesignIntentTypes", None)
    if intents is not None and getattr(design, "designIntent", None) != intents.HybridDesignIntentType:
        raise doc.DocumentError(
            "Gears with movable components and construction history need a Hybrid design. "
            "Choose Hybrid in Fusion's New Design options, with Capture Design History enabled, "
            "then open Gear Studio. Your current design has not been changed."
        )
    timeline = design.timeline
    if timeline.markerPosition != timeline.count:
        raise doc.DocumentError("Move the timeline marker to the end before creating or updating a gear.")


def _components(component):
    yield component
    for occurrence in doc._items(component.occurrences):
        yield from _components(occurrence.component)


def _generation(record):
    generations = [occurrence for occurrence in doc._items(record.component.occurrences)
                   if occurrence.attributes.itemByName(doc.ATTRIBUTE_GROUP, GENERATION)]
    if len(generations) != 1:
        raise doc.DocumentError("This gear's construction component is missing or duplicated. Undo that change before updating.")
    return generations[0]


def _external_state(design, old_components, old_generation):
    """Include sketches, datums and joints, not just solid features.

    Fusion can cascade a deletion rather than leave a failed dependent feature.
    Retain handles so either behavior forces a transaction abort.
    """
    result = []
    for component in doc._items(design.allComponents):
        if any(doc._same(component, old) for old in old_components):
            continue
        for name in ("features", "sketches", "constructionPlanes", "constructionAxes",
                     "constructionPoints", "joints", "asBuiltJoints", "occurrences"):
            for entity in doc._items(getattr(component, name, None)):
                if not doc._same(entity, old_generation) and doc._valid(entity):
                    result.append((entity, getattr(entity, "healthState", None)))
    return result


def _freeze_previous_diameters(components, applied_values):
    """Keep the old construction at its last built size while staging an update.

    A newly valid bore could exceed the OLD gear's root diameter. Detach only
    our tagged diameter bindings before changing user inputs. Fusion's command
    transaction restores these expressions too if any later operation fails.
    Restoring last-applied values also repairs pending live bore edits before
    replacing the old construction. External sketches are never modified here.
    """
    for component in components:
        for sketch in doc._items(getattr(component, "sketches", None)):
            for dimension in doc._items(sketch.sketchDimensions):
                attribute = dimension.attributes.itemByName(doc.ATTRIBUTE_GROUP, DIAMETER_INPUT)
                if attribute:
                    field = attribute.value
                    value = applied_values.get(field)
                    if field != "bore" or value is None or not math.isfinite(value) or value <= 0:
                        raise doc.DocumentError("The saved driving diameter is invalid. Undo the parameter edit before updating.")
                    dimension.parameter.expression = doc._unit_literal(value, "mm")


def commit_history(design, spec, values, candidate_body, record=None):
    """Replay the checked construction; preserve the outer gear's placement.

    Update stages a new generation before deleting the old one. Deletion is part
    of the caller's abortable native transaction. References outside the old
    generation must survive without new errors, otherwise the update is aborted.
    """
    require_component_design(design)
    doc._check_spec(spec)
    doc._assert_body(candidate_body)
    if not getattr(candidate_body, "isTemporary", False):
        raise doc.DocumentError("Prepare a detached candidate before committing native construction.")
    spec = deepcopy(spec)
    if record:
        record = doc.find_record(design, record.id)
        if record.construction != "native_history":
            raise doc.DocumentError("Duplicate this legacy gear to create a gear with construction history.")
        if spec.get("id") != record.id or spec["kind"] != record.spec["kind"]:
            raise doc.DocumentError("Duplicate the gear to change its family.")
        names = record.parameter_names
        old_generation = _generation(record)
        old_components = list(_components(old_generation.component))
    else:
        spec["id"] = str(uuid.uuid4())
        names = doc._parameter_names(design, spec)
        old_generation, old_components = None, []
    resolved = doc.resolve_spec(design, spec, names)
    if values.keys() != resolved.keys() or any(not math.isclose(values[k], resolved[k], rel_tol=1e-9, abs_tol=1e-9) for k in values):
        raise doc.DocumentError("Gear parameters changed during preparation. Validate and build again.")
    core, fusion = doc._api()
    import adsk
    external_health = _external_state(design, old_components, old_generation)
    try:
        if record:
            _freeze_previous_diameters(old_components, record.applied_values)
        doc._apply_parameters(design, spec, names, values, creating=record is None)
        if record:
            container = record.component
        else:
            occurrence = design.rootComponent.occurrences.addNewComponent(core.Matrix3D.create())
            occurrence.isGroundToParent = False
            container = occurrence.component
        start = design.timeline.count
        generation = container.occurrences.addNewComponent(core.Matrix3D.create())
        generation.component.name = "Construction"
        generation.isGroundToParent = True
        doc._check_success(generation.attributes.add(doc.ATTRIBUTE_GROUP, GENERATION, "1"), "Could not identify the construction component.")
        limit = 80000000 if spec["kind"] in ("crown", "worm_wheel") else 2000000
        # No event pumping inside the commit transaction. No document switching,
        # command re-entry, or creation replay from HTML readiness callbacks.
        with bounded(seconds=150, iterations=limit):
            body = generate_native(generation.component, spec["kind"], values, adsk, parameter_names=names)
            _verify_solid(body)
        body.name = spec.get("name") or "Gear"
        body.parentComponent.name = "Gear body and sketches"
        container.name = spec.get("name") or "Gear"
        # Every generated occurrence is fixed within the movable outer gear.
        for component in _components(generation.component):
            component.isSketchFolderLightBulbOn = True
            for child in doc._items(component.occurrences):
                child.isGroundToParent = True
        container.isSketchFolderLightBulbOn = True
        end = design.timeline.count - 1
        if end >= start:
            group = design.timeline.timelineGroups.add(start, end)
            group.name = "Gear Studio: " + container.name
            group.isCollapsed = False
        doc._write_metadata(container, doc._metadata(spec, names, values, "native_history"))
        doc._check_success(design.computeAll(), "Fusion could not compute the new construction.")
        new_health = [(feature, None) for component in _components(generation.component)
                      for feature in doc._items(component.features)]
        doc._check_health(external_health + new_health)
        if old_generation:
            doc._check_success(old_generation.deleteMe(), "Fusion could not replace the previous construction.")
            doc._check_success(design.computeAll(), "Fusion could not recompute the updated gear.")
            if any(not doc._valid(feature) for feature, _ in external_health):
                raise doc.DocumentError("Updating would delete a feature outside this gear's construction. Remove its generated-face references first.")
            doc._check_health(external_health + new_health)
        design.rootComponent.isSketchFolderLightBulbOn = True
        doc._check_success(design.activateRootComponent(), "Fusion could not return to the top-level Design workspace.")
        return doc.GearRecord(spec, container, container, dict(names), dict(values), "native_history")
    except Exception as exc:
        # The caller aborts the *whole* Fusion command transaction. Do not claim
        # restoration here, before Fusion has processed executeFailed.
        raise doc.DocumentError("Fusion could not finish the construction-history update. The command will be rolled back. " + str(exc)) from exc
