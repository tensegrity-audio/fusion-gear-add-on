"""Gear definitions, native expression inputs and recoverable document commits.

The stable API uses ordinary UserParameters and BaseFeature.updateBody. Updates
are explicit and must run inside a Fusion command execute handler (one undo item).
No CustomFeatures preview APIs or automatic geometry recomputation are used.

Host units: evaluateExpression returns centimetres for lengths and radians for
angles. Public numeric values in this module are millimetres/degrees/scalars.
Source bodies are accessed ONLY while their BaseFeature is in edit mode.

API references (Autodesk, checked September 2026):
https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_BaseFeature_updateBody.htm
https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_BaseFeature_bodies.htm
https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/core_UnitsManager_evaluateExpression.htm
https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_UserParameters_add.htm
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import math
import re
import uuid

from ..core.catalog import FIELDS, FAMILY_BY_ID

ATTRIBUTE_GROUP = "GearStudio"
ATTRIBUTE_NAME = "definition"
MAX_EXPRESSION_LENGTH = 512
MAX_METADATA_LENGTH = 32768
MAX_PARAMETER_GRAPH = 4096
MAX_DEPENDENCY_DEPTH = 32
# Native names may contain Unicode letters, $, degree symbols and quotes.
# A number's scientific-notation exponent is never a parameter token.
_NAME = re.compile(r'(?<![\w$\u00b0\u00b5"])(?:[^\W\d]|[$\u00b0"])[\w$\u00b0\u00b5"]*')
_ID = re.compile(r"[A-Za-z0-9_-]{8,64}\Z")


class DocumentError(ValueError):
    """Actionable failure that the command bridge may display directly."""


@dataclass
class GearRecord:
    spec: dict
    component: object
    feature: object
    parameter_names: dict
    applied_values: dict

    @property
    def id(self):
        return self.spec["id"]

    @property
    def name(self):
        return self.spec.get("name", "Gear")


def _api():
    # Lazy imports keep geometry-independent tests usable outside Fusion.
    import adsk.core
    import adsk.fusion
    return adsk.core, adsk.fusion


def _items(collection):
    if collection is None:
        return []
    if isinstance(collection, (list, tuple)):
        return list(collection)
    return [collection.item(index) for index in range(collection.count)]


def _valid(entity):
    return entity is not None and getattr(entity, "isValid", True)


def _same(a, b):
    return a is b or (a is not None and b is not None and a == b)


def _native(entity):
    return getattr(entity, "nativeObject", None) or entity


def _parameter_names(spec):
    identity = str(spec.get("id", ""))
    if not _ID.fullmatch(identity):
        raise DocumentError("This gear has an invalid identity. Duplicate it as a new gear.")
    prefix = re.sub(r"[^A-Za-z0-9]", "", identity)[:12]
    return {key: "GS_%s_%s" % (prefix, key) for key in spec["parameters"]}


def _check_spec(spec):
    if not isinstance(spec, dict) or spec.get("schema_version") != 1:
        raise DocumentError("This gear definition has an unsupported version.")
    family = FAMILY_BY_ID.get(spec.get("kind"))
    if not family:
        raise DocumentError("Choose a supported gear family.")
    parameters = spec.get("parameters")
    if not isinstance(parameters, dict) or set(parameters) != set(family["fields"]):
        raise DocumentError("The gear's parameter fields do not match its family. Reload the gear definition.")
    for field, expression in parameters.items():
        _check_expression(expression, FIELDS[field]["label"])
    if not isinstance(spec.get("name", ""), str) or len(spec.get("name", "")) > 160:
        raise DocumentError("Use a gear name no longer than 160 characters.")


def _check_expression(expression, label):
    if not isinstance(expression, str) or not expression.strip():
        raise DocumentError("%s: enter a number or parameter expression." % label)
    if len(expression) > MAX_EXPRESSION_LENGTH or any(char in expression for char in "\n\r\x00"):
        raise DocumentError("%s: use a single-line expression of at most %d characters." % (label, MAX_EXPRESSION_LENGTH))


def _unit_literal(value, unit):
    return "(%.17g%s)" % (value, " " + unit if unit else "")


def _from_internal(value, unit):
    if unit == "mm":
        return value * 10.0
    if unit == "deg":
        return math.degrees(value)
    return value


def _evaluate_native(manager, expression, unit, label):
    try:
        if not manager.isValidExpression(expression, unit):
            raise DocumentError("%s: the expression is invalid or has incompatible units. Check named parameters and units." % label)
        value = float(manager.evaluateExpression(expression, unit))
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError("%s: Fusion could not evaluate the expression. Check its syntax, units and referenced parameters." % label) from exc
    if not math.isfinite(value) or abs(value) > 1e15:
        raise DocumentError("%s: the expression must produce a finite, bounded number." % label)
    return _from_internal(value, unit)


class _Resolver:
    """Resolve pending aliases without modifying or trusting old host values.

    Pending owned parameter expressions overlay the host dependency graph. Any
    external parameter chain that reaches a pending alias is evaluated against
    that same overlay. Untouched external values use Fusion's own parser. This
    avoids old snapshots and catches direct and transitive dependency cycles.
    """
    def __init__(self, design, spec, parameter_names):
        self.manager = design.unitsManager
        self.parameters = spec["parameters"]
        self.names = parameter_names or (_parameter_names(spec) if spec.get("id") else {})
        if set(self.names) - set(self.parameters) or len(set(self.names.values())) != len(self.names):
            raise DocumentError("The gear's saved parameter names are inconsistent. Reload its definition.")
        self.aliases = {name: field for field, name in self.names.items()}
        self.external = {}
        for item in _items(getattr(design, "allParameters", None)):
            if len(self.external) >= MAX_PARAMETER_GRAPH:
                raise DocumentError("The design has too many parameters for a bounded dependency check. Use a smaller design.")
            self.external[item.name] = item
        self.memo = {}
        self.reachability = {}
        self.dependency_edges = 0
        self.active = []
        self.order = []
        self.nodes = 0

    def _expand(self, expression):
        # Managed names are restricted to plain identifiers, so boundaries do
        # not confuse GS_12_module with GS_12_module_backup.
        def replace(match):
            name = match.group(0)
            if name in self.aliases:
                field = self.aliases[name]
                value = self.field(field)
                return _unit_literal(value, FIELDS[field]["unit"])
            if name in self.external:
                item = self.external[name]
                if self._reaches_pending(name, set()):
                    value, unit = self.external_value(name, item)
                    return _unit_literal(value, unit)
            return name
        expanded = _NAME.sub(replace, expression)
        if len(expanded) > 8192:
            raise DocumentError("The expanded expression is too complex. Split it into simpler inputs.")
        return expanded

    def _reaches_pending(self, name, visiting):
        if name in self.aliases:
            return True
        if name not in self.external:
            return False
        if name in self.reachability:
            return self.reachability[name]
        if name in visiting:
            raise DocumentError("Circular parameter dependency detected. Remove the reference loop before building.")
        if len(visiting) >= MAX_DEPENDENCY_DEPTH:
            raise DocumentError("Parameter dependencies are too deeply nested. Simplify the expression chain.")
        visiting = visiting | {name}
        expression = getattr(self.external[name], "expression", "")
        _check_expression(expression, "Referenced parameter")
        reaches = False
        # Cache completed nodes, including negative results. A repeated DAG
        # such as Pn = Pprev + Pprev must be linear in graph size, not 2**n.
        # Visit all named edges even after finding a pending alias so cycles
        # and excessive work elsewhere in the same expression are detected.
        native_dependencies = getattr(self.external[name], "dependencyParameters", None)
        dependencies = ({item.name for item in _items(native_dependencies)} if native_dependencies is not None
                        else set(_NAME.findall(expression)))
        for token in dependencies:
            self.dependency_edges += 1
            if self.dependency_edges > MAX_PARAMETER_GRAPH * 4:
                raise DocumentError("The parameter dependency graph exceeds the supported work budget.")
            reaches = self._reaches_pending(token, visiting) or reaches
        self.reachability[name] = reaches
        return reaches

    def _enter(self, name):
        if name in self.active:
            raise DocumentError("Circular parameter dependency: %s. Remove this reference loop." % " -> ".join(self.active + [name]))
        if len(self.active) >= MAX_DEPENDENCY_DEPTH:
            raise DocumentError("Parameter dependencies are too deeply nested. Simplify the expression chain.")
        self.nodes += 1
        if self.nodes > MAX_PARAMETER_GRAPH:
            raise DocumentError("The parameter dependency graph exceeds the supported work budget.")
        self.active.append(name)

    def field(self, field):
        name = self.names.get(field, "input_" + field)
        if name in self.memo:
            return self.memo[name]
        self._enter(name)
        try:
            expression = self._expand(self.parameters[field])
            value = _evaluate_native(self.manager, expression, FIELDS[field]["unit"], FIELDS[field]["label"])
            self.memo[name] = value
            self.order.append(field)
            return value
        finally:
            self.active.pop()

    def external_value(self, name, item):
        unit = getattr(item, "unit", "")
        if unit in ("", "unitless"):
            canonical = ""
        elif self.manager.areUnitsCompatible(unit, "mm"):
            canonical = "mm"
        elif self.manager.areUnitsCompatible(unit, "deg"):
            canonical = "deg"
        else:
            raise DocumentError("A parameter that depends on this gear uses unsupported units. Use length, angle or unitless intermediate parameters.")
        memo_key = "external:" + name
        if memo_key in self.memo:
            return self.memo[memo_key], canonical
        self._enter(name)
        try:
            expression = self._expand(item.expression)
            # Bare numeric expressions in an external parameter retain that
            # parameter's own display units before conversion to canonical units.
            internal = _evaluate_native(self.manager, expression, unit, name)
            if unit not in ("", "mm", "deg"):
                internal = _from_internal(internal, canonical)
            self.memo[memo_key] = internal
            return internal, canonical
        finally:
            self.active.pop()


def resolve_spec(design, spec, parameter_names=None):
    """Read-only resolution with native Fusion expressions, in mm/deg/scalars."""
    _check_spec(spec)
    resolver = _Resolver(design, spec, parameter_names)
    return {field: resolver.field(field) for field in spec["parameters"]}


def _record(feature, component):
    attribute = feature.attributes.itemByName(ATTRIBUTE_GROUP, ATTRIBUTE_NAME)
    if not attribute:
        return None
    try:
        if len(attribute.value) > MAX_METADATA_LENGTH:
            raise ValueError("oversize")
        data = json.loads(attribute.value)
        if data.get("schema_version") != 1:
            raise ValueError("version")
        spec = data["spec"]
        _check_spec(spec)
        names = data["parameter_names"]
        if set(names) != set(spec["parameters"]) or any(not isinstance(name, str) or not re.fullmatch(r"GS_[A-Za-z0-9_]+", name) for name in names.values()):
            raise ValueError("parameter names")
        if len(set(names.values())) != len(names):
            raise ValueError("duplicate parameter names")
        if not _ID.fullmatch(str(spec.get("id", ""))):
            raise ValueError("identity")
        values = data["applied_values"]
        if set(values) != set(spec["parameters"]) or any(type(value) not in (int, float) or not math.isfinite(value) for value in values.values()):
            raise ValueError("applied values")
    except Exception as exc:
        raise DocumentError("A Gear Studio definition is damaged or from an unsupported version. Restore an earlier document version or remove its gear before continuing.") from exc
    return GearRecord(deepcopy(spec), component, feature, dict(names), dict(values))


def records(design):
    """Definitions are owned by BaseFeatures, never fragile face identifiers."""
    result = []
    components = _items(getattr(design, "allComponents", None))
    if not components and getattr(design, "rootComponent", None):
        components = [design.rootComponent]
    for component in components:
        if not _valid(component):
            continue
        for feature in _items(component.features.baseFeatures):
            if _valid(feature):
                record = _record(feature, component)
                if record:
                    result.append(record)
    identities = [record.id for record in result]
    if len(identities) != len(set(identities)):
        raise DocumentError("Two gears share a copied identity. Use Gear Studio's Duplicate Gear command to create independent gears, or undo the component copy.")
    aliases = [alias for record in result for alias in record.parameter_names.values()]
    if len(aliases) != len(set(aliases)):
        raise DocumentError("Two gears share parameter names. Restore their independent definitions before updating.")
    return result


def find_record(design, identity):
    matches = [record for record in records(design) if record.id == identity]
    if not matches:
        raise DocumentError("This gear no longer exists in the active document. Select a gear from this document or create a new one.")
    return matches[0]


def current_spec(design, record):
    """Take actual userParameter.expression values, preserving live references."""
    spec = deepcopy(record.spec)
    for field, name in record.parameter_names.items():
        parameter = design.userParameters.itemByName(name)
        if parameter is None or not _valid(parameter):
            raise DocumentError("Parameter '%s' is missing or renamed. Restore that name in Fusion Parameters before updating this gear." % name)
        spec["parameters"][field] = parameter.expression
    _check_spec(spec)
    return spec


def selected_record(app):
    design = app.activeProduct
    if design is None or not hasattr(design, "rootComponent"):
        return None
    known = records(design)
    selected = _items(app.userInterface.activeSelections)
    if not selected:
        return None
    found = {}
    for selection in selected:
        entity = _native(selection.entity)
        if getattr(entity, "body", None) is not None:
            entity = _native(entity.body)  # Face or edge.
        direct = [record for record in known if _same(entity, record.feature)]
        if not direct:
            component = getattr(entity, "component", None)
            if component is None and hasattr(entity, "features") and hasattr(entity, "bRepBodies"):
                component = entity
            if component is not None:
                direct = [record for record in known if _same(_native(component), record.component)]
            else:
                associated = getattr(entity, "baseFeature", None)
                for record in known:
                    if _same(_native(associated), record.feature) or any(_same(entity, _native(body)) for body in _items(record.feature.bodies)):
                        direct.append(record)
                # Do not guess from parentComponent: a Part Design can contain
                # an unrelated box alongside one gear. A downstream body whose
                # provenance is unavailable must be selected by its component
                # or owned timeline feature instead.
        if len(direct) > 1:
            raise DocumentError("This selection contains more than one gear. Select one gear body or its Gear Studio timeline feature.")
        if direct:
            found[direct[0].id] = direct[0]
    if len(found) > 1:
        raise DocumentError("Multiple gears are selected. Select a single gear to edit or update.")
    return next(iter(found.values()), None)


def _check_design(design):
    _, fusion = _api()
    if design.designType != fusion.DesignTypes.ParametricDesignType:
        raise DocumentError("Enable Capture Design History before building editable gears. Gear Studio will not change the design mode automatically.")
    document = getattr(design, "parentDocument", None)
    if document is not None and getattr(document, "isReadOnly", False):
        raise DocumentError("This document is read-only. Open an editable local design before building.")


def _assert_body(body):
    if not _valid(body) or not getattr(body, "isSolid", False):
        raise DocumentError("The candidate is not a valid B-rep solid. The existing gear was not changed.")
    if getattr(body, "lumps", None) is not None and body.lumps.count != 1:
        raise DocumentError("The candidate contains disconnected solids. Adjust the gear dimensions before rebuilding.")


def _check_success(result, message):
    if result is False or result is None:
        raise DocumentError(message)
    return result


def _metadata(spec, names, values):
    data = json.dumps({"schema_version": 1, "spec": spec, "parameter_names": names,
                       "applied_values": values}, separators=(",", ":"), allow_nan=False)
    if len(data) > MAX_METADATA_LENGTH:
        raise DocumentError("The gear definition is too large to save. Simplify its expressions.")
    return data


def _write_metadata(feature, text):
    result = feature.attributes.add(ATTRIBUTE_GROUP, ATTRIBUTE_NAME, text)
    _check_success(result, "Fusion could not save the gear definition.")


def _parameter_snapshot(design, names):
    return {name: (design.userParameters.itemByName(name).expression if design.userParameters.itemByName(name) else None)
            for name in names.values()}


def _apply_parameters(design, spec, names, values, creating=False):
    core, _ = _api()
    resolver = _Resolver(design, spec, names)
    for field in spec["parameters"]:
        resolver.field(field)
    for field, name in names.items():
        parameter = design.userParameters.itemByName(name)
        if parameter and creating:
            raise DocumentError("Parameter '%s' already exists. Rename it or create a new independent gear." % name)
        if not parameter and not creating:
            raise DocumentError("Parameter '%s' is missing. Restore it before updating the gear." % name)
    # Break old owned references with validated literal seeds. This permits
    # reversing an acyclic dependency direction without transient old cycles.
    for field, name in names.items():
        literal = _unit_literal(values[field], FIELDS[field]["unit"])
        parameter = design.userParameters.itemByName(name)
        if parameter:
            parameter.expression = literal
        else:
            parameter = design.userParameters.add(name, core.ValueInput.createByString(literal), FIELDS[field]["unit"],
                                                  "Gear Studio | %s | %s | Apply with Update Gear" % (spec.get("name", "Gear"), FIELDS[field]["label"]))
            _check_success(parameter, "Fusion could not create parameter '%s'." % name)
    for field in resolver.order:
        design.userParameters.itemByName(names[field]).expression = spec["parameters"][field]
    # The native table is authoritative. Verify no host unit interpretation or
    # expression normalization changed the body inputs before geometry commits.
    for field, name in names.items():
        parameter = design.userParameters.itemByName(name)
        actual = _from_internal(float(parameter.value), FIELDS[field]["unit"])
        if not math.isclose(actual, values[field], rel_tol=1e-8, abs_tol=1e-8):
            raise DocumentError("Fusion interpreted '%s' differently from the validated value. Add explicit units to the expression." % name)


def _restore_parameters(design, spec, names, snapshot):
    failures = []
    existing = {field: snapshot[name] for field, name in names.items() if snapshot[name] is not None}
    if existing:
        old_spec = deepcopy(spec)
        old_spec["parameters"] = existing
        try:
            resolver = _Resolver(design, old_spec, {field: names[field] for field in existing})
            restored = {field: resolver.field(field) for field in existing}
            for field in existing:
                parameter = design.userParameters.itemByName(names[field])
                if parameter is None:
                    raise DocumentError("A parameter disappeared during recovery.")
                parameter.expression = _unit_literal(restored[field], FIELDS[field]["unit"])
            for field in resolver.order:
                design.userParameters.itemByName(names[field]).expression = existing[field]
        except Exception as exc:
            failures.append("parameter expressions: %s" % exc)
    # A failed creation has no pre-existing external references to its aliases.
    # Remove dependencies first, then delete new rows in reverse creation order.
    new_names = [name for name, previous in snapshot.items() if previous is None]
    for name in new_names:
        parameter = design.userParameters.itemByName(name)
        if parameter is not None:
            try:
                field = next(field for field, alias in names.items() if alias == name)
                parameter.expression = _unit_literal(0, FIELDS[field]["unit"])
            except Exception as exc:
                failures.append("new parameter reset: %s" % exc)
    for name in reversed(new_names):
        parameter = design.userParameters.itemByName(name)
        if parameter is not None:
            try:
                _check_success(parameter.deleteMe(), "Could not remove a new parameter.")
            except Exception as exc:
                failures.append("new parameter removal: %s" % exc)
    return failures


def _health_snapshot(design):
    snapshot = []
    for component in _items(getattr(design, "allComponents", None)):
        for feature in _items(component.features):
            if _valid(feature):
                snapshot.append((feature, getattr(feature, "healthState", None)))
    return snapshot


def _check_health(snapshot):
    _, fusion = _api()
    errors = getattr(getattr(fusion, "FeatureHealthStates", None), "ErrorFeatureHealthState", None)
    if errors is None:
        return
    for feature, previous in snapshot:
        if _valid(feature) and getattr(feature, "healthState", None) == errors and previous != errors:
            raise DocumentError("Updating this gear breaks downstream feature '%s'. Remove or revise its tooth-face references, then retry." % getattr(feature, "name", "unnamed"))


def _dedicated_gear_component(design, record):
    """Rename only a leaf component containing this gear's single result body.

    Check at the user's timeline position, before rolling back to the gear.
    Otherwise later bodies/children could be hidden and a shared parent could
    incorrectly appear to belong entirely to this gear.
    """
    component = record.component
    if _same(component, design.rootComponent):
        return False
    children = getattr(component, "occurrences", None)
    if children is None or children.count or component.bRepBodies.count != 1:
        return False
    if record.feature.bodies.count != 1 or not _same(record.feature.bodies.item(0), component.bRepBodies.item(0)):
        return False
    owned = [feature for feature in _items(component.features.baseFeatures)
             if feature.attributes.itemByName(ATTRIBUTE_GROUP, ATTRIBUTE_NAME)]
    return len(owned) == 1 and _same(owned[0], record.feature)


def commit_candidate(design, spec, values, candidate_body, record=None):
    """Commit a detached solid, restoring source body and inputs on failure.

    Run within the caller's command.execute handler for Fusion undo grouping.
    Existing component/occurrence placement is never replaced or reset. Faces
    can change identity when tooth topology changes; downstream error states are
    checked and cause a rollback. If Fusion itself refuses recovery, the caller
    must surface the recovery error and direct the user to Undo.
    """
    _check_design(design)
    _check_spec(spec)
    _assert_body(candidate_body)
    if not getattr(candidate_body, "isTemporary", True):
        raise DocumentError("Build a detached candidate solid before committing the gear.")
    spec = deepcopy(spec)
    if record is not None:
        current = find_record(design, record.id)
        if spec.get("id") != current.id or spec["kind"] != current.spec["kind"]:
            raise DocumentError("Changing an existing gear's identity or family is unsupported. Duplicate it as a new gear.")
        record = current
        names = dict(record.parameter_names)
    else:
        # Always generate a fresh identity for creation. The UI may have an old
        # draft ID; it must never accidentally claim another gear's parameters.
        spec["id"] = str(uuid.uuid4())
        names = _parameter_names(spec)
    resolved = resolve_spec(design, spec, names)
    if set(values) != set(resolved) or any(not math.isclose(float(values[key]), resolved[key], rel_tol=1e-9, abs_tol=1e-9) for key in resolved):
        raise DocumentError("Gear parameters changed while building. Validate and build again to use the current values.")
    values = resolved
    metadata = _metadata(spec, names, values)
    snapshot = _parameter_snapshot(design, names)
    health = _health_snapshot(design)
    core, fusion = _api()
    manager = fusion.TemporaryBRepManager.get()
    feature = record.feature if record else None
    component = record.component if record else None
    occurrence = None
    backup = None
    source = None
    editing = False
    changed_body = False
    created_feature = False
    parameters_started = False
    metadata_attempted = False
    rename = record is not None and spec.get("name") != record.spec.get("name")
    rename_component = rename and _dedicated_gear_component(design, record)
    previous_names = {}
    renamed = set()
    old_metadata = feature.attributes.itemByName(ATTRIBUTE_GROUP, ATTRIBUTE_NAME).value if feature else None
    timeline = design.timeline
    old_marker = timeline.markerPosition
    try:
        if record:
            if not _valid(feature) or getattr(feature, "isSuppressed", False):
                raise DocumentError("The gear's source feature is missing or suppressed. Restore it before updating.")
            _check_success(feature.timelineObject.rollTo(False), "Fusion could not access the gear's timeline position.")
            if rename:
                if feature.bodies.count != 1:
                    raise DocumentError("The gear's result body is unavailable. Restore its source feature before renaming it.")
                previous_names = {"result": feature.bodies.item(0).name, "feature": feature.name}
                if rename_component:
                    previous_names["component"] = component.name
        else:
            intents = getattr(fusion, "DesignIntentTypes", None)
            intent = getattr(design, "designIntent", None)
            if intents is not None and intent == intents.PartDesignIntentType:
                component = design.rootComponent
            elif intents is not None and intent == intents.AssemblyDesignIntentType:
                raise DocumentError("Use a Part or Hybrid design for editable gear bodies. Open a modelable part or enable modeling before building.")
            else:
                occurrence = design.rootComponent.occurrences.addNewComponent(core.Matrix3D.create())
                _check_success(occurrence, "Fusion could not create the gear component. Use a Part or Hybrid design.")
                component = occurrence.component
                component.name = spec.get("name") or "Gear"
            feature = component.features.baseFeatures.add()
            _check_success(feature, "Fusion could not create an editable gear feature.")
            created_feature = True
            feature.name = "Gear Studio: " + (spec.get("name") or "Gear")
        _check_success(feature.startEdit(), "Fusion could not enter the gear's source feature. Finish the current edit and try again.")
        editing = True
        if record:
            if feature.bodies.count != 1:
                raise DocumentError("The gear's source feature no longer contains exactly one body. Undo manual source-body changes before updating.")
            source = feature.bodies.item(0)
            _assert_body(source)
            if rename:
                previous_names["source"] = source.name
            backup = manager.copy(source)
            _assert_body(backup)
        parameters_started = True
        _apply_parameters(design, spec, names, values, creating=record is None)
        if record:
            # Mark before the call because a failing host call may have changed
            # the source despite returning false or throwing an exception.
            changed_body = True
            _check_success(feature.updateBody(source, candidate_body), "Fusion rejected the replacement solid. The previous gear will be restored.")
            if rename:
                renamed.add("source")
                source.name = spec.get("name") or "Gear"
        else:
            source = component.bRepBodies.add(candidate_body, feature)
            _check_success(source, "Fusion could not add the solid to its source feature.")
            source.name = spec.get("name") or "Gear"
        _assert_body(source)
        _check_success(feature.finishEdit(), "Fusion could not finish the gear's source feature.")
        editing = False
        if rename:
            if feature.bodies.count != 1:
                raise DocumentError("Fusion did not return exactly one gear body after the update.")
            renamed.add("result")
            feature.bodies.item(0).name = spec.get("name") or "Gear"
            renamed.add("feature")
            feature.name = "Gear Studio: " + (spec.get("name") or "Gear")
            if rename_component:
                renamed.add("component")
                component.name = spec.get("name") or "Gear"
        metadata_attempted = True
        _write_metadata(feature, metadata)
        if record:
            timeline.markerPosition = old_marker
        _check_success(design.computeAll(), "Fusion could not recompute the design after the gear update.")
        _check_health(health + [(feature, None)])
        return GearRecord(spec, component, feature, names, dict(values))
    except Exception as original:
        recovery = []
        if record and backup is not None and changed_body:
            try:
                if not editing:
                    _check_success(feature.timelineObject.rollTo(False), "Could not return to source feature.")
                    _check_success(feature.startEdit(), "Could not re-enter source feature.")
                    editing = True
                if feature.bodies.count != 1:
                    raise DocumentError("Source-body count changed during recovery.")
                _check_success(feature.updateBody(feature.bodies.item(0), backup), "Fusion refused to restore the previous body.")
                if "source" in renamed:
                    feature.bodies.item(0).name = previous_names["source"]
            except Exception as exc:
                recovery.append("source solid: %s" % exc)
        if editing:
            try:
                _check_success(feature.finishEdit(), "Could not leave source-feature edit mode.")
            except Exception as exc:
                recovery.append("finish edit: %s" % exc)
        if renamed:
            # Source and result bodies can have distinct user-assigned names.
            # Restore the result name after finishing source edit, then only
            # the feature/component names that this operation actually touched.
            for role in ("result", "feature", "component"):
                if role not in renamed and not (role == "result" and "source" in renamed):
                    continue
                try:
                    entity = feature.bodies.item(0) if role == "result" else feature if role == "feature" else component
                    entity.name = previous_names[role]
                except Exception as exc:
                    recovery.append("%s name: %s" % (role, exc))
        if record and old_metadata is not None and metadata_attempted:
            try:
                _write_metadata(feature, old_metadata)
            except Exception as exc:
                recovery.append("saved definition: %s" % exc)
        if not record:
            try:
                if occurrence is not None and _valid(occurrence):
                    _check_success(occurrence.deleteMe(), "Could not remove the new component.")
                elif created_feature and _valid(feature):
                    _check_success(feature.deleteMe(), "Could not remove the new source feature.")
            except Exception as exc:
                recovery.append("new gear cleanup: %s" % exc)
        if parameters_started:
            recovery.extend(_restore_parameters(design, spec, names, snapshot))
        try:
            timeline.markerPosition = old_marker
            _check_success(design.computeAll(), "Could not recompute the restored design.")
        except Exception as exc:
            recovery.append("timeline recovery: %s" % exc)
        if recovery:
            raise DocumentError("The gear operation failed and Fusion could not completely restore the previous state. Use Undo now before continuing. Recovery details: " + "; ".join(recovery)) from original
        if isinstance(original, DocumentError):
            raise
        raise DocumentError("Fusion could not commit this gear. The previous geometry and parameters were restored. %s" % str(original)) from original
