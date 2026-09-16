"""Document-boundary contracts without pretending to run Fusion's B-rep kernel."""
from copy import deepcopy
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from GearStudio.core.catalog import default_spec, FIELDS
from GearStudio.core.expressions import evaluate, Quantity
from GearStudio.fusion import document as d


class Collection:
    def __init__(self, items=()): self.items = list(items)
    @property
    def count(self): return len(self.items)
    def item(self, index): return self.items[index]


class Attribute:
    def __init__(self, value): self.value = value


class Attributes:
    def __init__(self): self.data = {}; self.fail_next = False
    def itemByName(self, group, name): return self.data.get((group, name))
    def add(self, group, name, value):
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("injected metadata failure")
        self.data[group, name] = Attribute(value)
        return self.data[group, name]


class Parameter:
    def __init__(self, owner, name, expression, unit):
        self.owner, self.name, self.unit = owner, name, unit
        self._expression = expression
        self.isValid = True
    @property
    def expression(self): return self._expression
    @expression.setter
    def expression(self, expression):
        self.owner.design.require_parameter_mode()
        if self.owner.fail_on == (self.name, expression):
            self.owner.fail_on = None
            raise RuntimeError("injected parameter failure")
        self._expression = expression
    @property
    def value(self):
        return self.owner.design.unitsManager.evaluateExpression(self.expression, self.unit)
    def deleteMe(self):
        self.owner.design.require_parameter_mode()
        del self.owner.data[self.name]
        return True


class Parameters:
    def __init__(self, design): self.design = design; self.data = {}; self.fail_on = None
    @property
    def count(self): return len(self.data)
    def item(self, index): return list(self.data.values())[index]
    def itemByName(self, name): return self.data.get(name)
    def add(self, name, value, unit, comment):
        self.design.require_parameter_mode()
        if name in self.data: raise ValueError("duplicate")
        parameter = Parameter(self, name, value, unit)
        self.data[name] = parameter
        return parameter


class Units:
    def __init__(self, design): self.design = design; self.stack = []
    def evaluateExpression(self, expression, unit):
        # Resolve just referenced host parameters, preserving unit dimensions.
        variables = {}
        for name in set(d._NAME.findall(expression)):
            param = self.design.allParameters.itemByName(name)
            if param:
                if name in self.stack: raise ValueError("host cycle")
                self.stack.append(name)
                try:
                    value = param.value
                finally:
                    self.stack.pop()
                if param.unit in ("mm", "cm"):
                    variables[name] = Quantity(value * 10, "length")
                elif param.unit in ("deg", "rad"):
                    variables[name] = Quantity(value, "angle")
                else:
                    variables[name] = Quantity(value)
        canonical = "mm" if unit == "cm" else "deg" if unit == "rad" else unit
        value = evaluate(expression, canonical, variables)
        # Fake handles dimensional cm/rad expressions used in tests. The actual
        # host, not this fake, defines every Fusion expression grammar detail.
        if canonical == "mm": return value / 10
        if canonical == "deg": return math.radians(value)
        return value
    def isValidExpression(self, expression, unit):
        try: self.evaluateExpression(expression, unit); return True
        except (ValueError, ArithmeticError): return False
    def areUnitsCompatible(self, a, b):
        return a == b or {a, b} <= {"mm", "cm", "in"} or {a, b} <= {"rad", "deg"}


class Body:
    isValid = True
    isSolid = True
    nativeObject = None
    def __init__(self, shape, temporary=False):
        self.shape, self.isTemporary = shape, temporary
        self.lumps = Collection([1])
        self.parentComponent = None


class Timeline:
    def __init__(self): self.markerPosition = 9


class Feature:
    isValid = True
    isSuppressed = False
    healthState = 0
    def __init__(self, component):
        self.component = component
        self.attributes = Attributes()
        self.bodies = Collection()
        self.name = "Gear source"
        self.editing = False
        self.fail_update = False
        self.fail_finish = False
        self.updates = []
        self.timelineObject = SimpleNamespace(rollTo=self.roll)
    def roll(self, before):
        self.component.design.timeline.markerPosition = 3
        return True
    def startEdit(self): self.editing = True; return True
    def finishEdit(self):
        if self.fail_finish:
            self.fail_finish = False
            return False
        self.editing = False
        return True
    def updateBody(self, source, candidate):
        assert self.editing, "Source modification outside edit mode"
        self.updates.append(candidate.shape)
        source.shape = candidate.shape
        if self.fail_update:
            self.fail_update = False
            return False  # Deliberately model a partial failed host mutation.
        return True
    def deleteMe(self):
        self.isValid = False
        self.component.features.items.remove(self)
        return True


class SplitBodyFeature(Feature):
    """Model Fusion's distinct source and result bodies for rename recovery."""
    @property
    def bodies(self):
        return self.source_bodies if self.editing else self.result_bodies

    def finishEdit(self):
        if not super().finishEdit():
            return False
        source, result = self.source_bodies.item(0), self.result_bodies.item(0)
        result.shape, result.name = source.shape, source.name
        return True


class Features(Collection):
    def __init__(self, component): super().__init__(); self.component = component
    @property
    def baseFeatures(self): return self
    def add(self):
        feature = Feature(self.component)
        self.items.append(feature)
        return feature


class Bodies(Collection):
    def __init__(self, component): super().__init__(); self.component = component
    def add(self, candidate, feature):
        assert feature.editing
        body = Body(candidate.shape)
        body.parentComponent = self.component
        self.items.append(body)
        feature.bodies.items.append(body)
        return body


class Component:
    isValid = True
    nativeObject = None
    def __init__(self, design):
        self.design = design
        self.features = Features(self)
        self.bRepBodies = Bodies(self)
        self.name = "Part"


class Design:
    designType = 1
    designIntent = 0
    def __init__(self):
        self.timeline = Timeline()
        self.rootComponent = Component(self)
        self.allComponents = Collection([self.rootComponent])
        self.userParameters = Parameters(self)
        self.allParameters = self.userParameters
        self.unitsManager = Units(self)
        self.fail_compute_once = False
        self.compute_hook = None
    def require_parameter_mode(self):
        # A BaseFeature edits direct geometry inside a parametric design. The
        # design's history setting alone does not establish parameter access.
        if any(feature.editing for component in self.allComponents.items
               for feature in component.features.items):
            raise RuntimeError("3 : this is not a parametric design")
    def computeAll(self):
        if self.compute_hook: self.compute_hook()
        if self.fail_compute_once:
            self.fail_compute_once = False
            return False
        return True


API = (SimpleNamespace(ValueInput=SimpleNamespace(createByString=lambda value: value),
                       Matrix3D=SimpleNamespace(create=lambda: object())),
       SimpleNamespace(DesignTypes=SimpleNamespace(ParametricDesignType=1),
                       DesignIntentTypes=SimpleNamespace(PartDesignIntentType=0, AssemblyDesignIntentType=1, HybridDesignIntentType=2),
                       FeatureHealthStates=SimpleNamespace(ErrorFeatureHealthState=2),
                       TemporaryBRepManager=SimpleNamespace(get=lambda: SimpleNamespace(copy=lambda source: Body(source.shape, True)))))


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.design = Design()
        self.spec = default_spec()
        self.api = patch.object(d, "_api", return_value=API)
        self.api.start()
        self.addCleanup(self.api.stop)
    def create(self):
        return d.commit_candidate(self.design, self.spec, d.resolve_spec(self.design, self.spec), Body("original", True))
    def updated(self, record):
        spec = deepcopy(record.spec)
        spec["parameters"]["teeth"] = "30"
        return spec, d.resolve_spec(self.design, spec, record.parameter_names)
    def move_to_dedicated_component(self, record):
        root = self.design.rootComponent
        component = Component(self.design)
        component.occurrences = Collection()
        component.name = "Original gear component"
        component.placement = {"x": 19, "angle": 0.7}
        body = record.feature.bodies.item(0)
        root.features.items.remove(record.feature)
        root.bRepBodies.items.remove(body)
        component.features.items.append(record.feature)
        component.bRepBodies.items.append(body)
        body.parentComponent = component
        record.feature.component = component
        record.component = component
        self.design.allComponents.items.append(component)
        return component
    def assert_restored(self, record, expressions):
        self.assertEqual(record.feature.bodies.item(0).shape, "original")
        self.assertFalse(record.feature.editing)
        self.assertEqual(self.design.timeline.markerPosition, 9)
        self.assertEqual(d.find_record(self.design, record.id).spec, record.spec)
        self.assertEqual({name: parameter.expression for name, parameter in self.design.userParameters.data.items()}, expressions)

    def test_host_units_are_converted_once(self):
        values = d.resolve_spec(self.design, self.spec)
        self.assertAlmostEqual(values["module"], 1)
        self.assertAlmostEqual(values["pressure_angle"], 20)
        self.assertEqual(values["teeth"], 24)

    def test_parameter_scanner_does_not_treat_exponents_as_names(self):
        self.assertEqual(d._NAME.findall("1e-3 mm + 2E4 mm + GS_abc_module"), ["mm", "mm", "GS_abc_module"])
        self.assertEqual(d._NAME.findall('$shaft + \u00b5Offset + tooth\u00b0'), ['$shaft', '\u00b5Offset', 'tooth\u00b0'])

    def test_pending_alias_uses_new_input_not_previous_table_value(self):
        record = self.create()
        spec = deepcopy(record.spec)
        spec["parameters"]["module"] = "2 mm"
        spec["parameters"]["width"] = record.parameter_names["module"] + " * 4"
        values = d.resolve_spec(self.design, spec, record.parameter_names)
        self.assertEqual(values["width"], 8)
        self.assertEqual(self.design.userParameters.itemByName(record.parameter_names["module"]).value, 0.1)

    def test_external_chain_referencing_pending_alias_is_resolved(self):
        record = self.create()
        alias = record.parameter_names["module"]
        self.design.userParameters.add("stock", alias + " * 3", "mm", "")
        self.design.userParameters.add("stockHalf", "stock / 2", "mm", "")
        spec = deepcopy(record.spec)
        spec["parameters"]["module"] = "4 mm"
        spec["parameters"]["width"] = "stockHalf + 1 mm"
        self.assertEqual(d.resolve_spec(self.design, spec, record.parameter_names)["width"], 7)

    def test_external_chain_cycle_rejected_before_mutation(self):
        record = self.create()
        self.design.userParameters.add("stock", record.parameter_names["module"] + " * 2", "mm", "")
        spec = deepcopy(record.spec)
        spec["parameters"]["module"] = "stock / 2"
        with self.assertRaisesRegex(d.DocumentError, "Circular"):
            d.resolve_spec(self.design, spec, record.parameter_names)
        self.assertEqual(record.feature.updates, [])

    def test_repeated_dependency_dag_has_bounded_linear_traversal(self):
        record = self.create()
        self.design.userParameters.add("P0", "1 mm", "mm", "")
        for index in range(1, 29):
            self.design.userParameters.add("P%d" % index,
                                           "P%d + P%d" % (index - 1, index - 1), "mm", "")
        resolver = d._Resolver(self.design, record.spec, record.parameter_names)
        self.assertFalse(resolver._reaches_pending("P28", set()))
        self.assertEqual(len(resolver.reachability), 29)
        self.assertLessEqual(resolver.dependency_edges, 30)
        previous = resolver.dependency_edges
        self.assertFalse(resolver._reaches_pending("P28", set()))
        self.assertEqual(resolver.dependency_edges, previous)

    def test_direct_pending_cycle_rejected(self):
        record = self.create()
        spec = deepcopy(record.spec)
        spec["parameters"]["module"] = record.parameter_names["width"]
        spec["parameters"]["width"] = record.parameter_names["module"]
        with self.assertRaisesRegex(d.DocumentError, "Circular"):
            d.resolve_spec(self.design, spec, record.parameter_names)

    def test_invalid_and_excessive_expressions_fail_read_only(self):
        for expression in ("", "a" * 513, "1 mm\n2 mm", "1/0", "20 deg"):
            with self.subTest(expression=expression):
                self.spec["parameters"]["module"] = expression
                with self.assertRaises(d.DocumentError): d.resolve_spec(self.design, self.spec)
        self.assertEqual(self.design.rootComponent.features.count, 0)
        self.assertEqual(self.design.userParameters.count, 0)

    def test_create_persists_one_feature_and_real_expression_parameters(self):
        record = self.create()
        self.assertIs(record.component, self.design.rootComponent)
        self.assertEqual(len(d.records(self.design)), 1)
        self.assertEqual(d.find_record(self.design, record.id).spec, record.spec)
        self.assertEqual(d.current_spec(self.design, record), record.spec)
        self.assertTrue(all(name.startswith("GS_") for name in record.parameter_names.values()))
        self.assertEqual(record.feature.bodies.item(0).shape, "original")
        self.assertFalse(record.feature.editing)

    def test_update_preserves_identity_body_and_expression_text(self):
        record = self.create()
        body = record.feature.bodies.item(0)
        spec, values = self.updated(record)
        spec["parameters"]["width"] = record.parameter_names["module"] + " * 9"
        values = d.resolve_spec(self.design, spec, record.parameter_names)
        updated = d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assertIs(updated.feature, record.feature)
        self.assertIs(updated.component, record.component)
        self.assertIs(updated.feature.bodies.item(0), body)
        self.assertEqual(updated.id, record.id)
        self.assertEqual(body.shape, "new")
        self.assertEqual(d.current_spec(self.design, updated)["parameters"]["width"], spec["parameters"]["width"])
        self.assertEqual(self.design.timeline.markerPosition, 9)

    def test_rename_updates_body_and_feature_without_renaming_part_root(self):
        record = self.create()
        self.design.rootComponent.name = "Drive assembly"
        spec, values = self.updated(record)
        spec["name"] = "Output gear"
        updated = d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assertEqual(updated.feature.name, "Gear Studio: Output gear")
        self.assertEqual(updated.feature.bodies.item(0).name, "Output gear")
        self.assertEqual(self.design.rootComponent.name, "Drive assembly")

    def test_rename_updates_dedicated_component_and_preserves_placement(self):
        record = self.create()
        component = self.move_to_dedicated_component(record)
        spec, values = self.updated(record)
        spec["name"] = "Pinion"
        updated = d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assertIs(updated.component, component)
        self.assertEqual(component.name, "Pinion")
        self.assertEqual(component.placement, {"x": 19, "angle": 0.7})

    def test_rename_does_not_change_shared_parent_with_another_body(self):
        record = self.create()
        component = self.move_to_dedicated_component(record)
        component.bRepBodies.items.append(Body("unrelated mounting plate"))
        spec, values = self.updated(record)
        spec["name"] = "Pinion"
        d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assertEqual(component.name, "Original gear component")
        self.assertEqual(record.feature.bodies.item(0).name, "Pinion")

    def test_rename_does_not_change_parent_with_a_child_component(self):
        record = self.create()
        component = self.move_to_dedicated_component(record)
        component.occurrences.items.append(object())
        spec, values = self.updated(record)
        spec["name"] = "Pinion"
        d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assertEqual(component.name, "Original gear component")

    def test_parameter_update_without_name_edit_preserves_manual_browser_names(self):
        record = self.create()
        component = self.move_to_dedicated_component(record)
        record.feature.name = "Manually named timeline node"
        record.feature.bodies.item(0).name = "Manually named solid"
        spec, values = self.updated(record)
        d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assertEqual(record.feature.name, "Manually named timeline node")
        self.assertEqual(record.feature.bodies.item(0).name, "Manually named solid")
        self.assertEqual(component.name, "Original gear component")

    def test_failed_rename_restores_exact_source_result_feature_and_component_names(self):
        for failure in ("metadata", "finish", "health"):
            with self.subTest(failure=failure):
                self.design = Design()
                record = self.create()
                component = self.move_to_dedicated_component(record)
                feature = record.feature
                result_body = feature.bodies.item(0)
                result_body.name = "Custom result name"
                source_body = Body("original")
                source_body.name = "Different source name"
                feature.source_bodies = Collection([source_body])
                feature.result_bodies = Collection([result_body])
                feature.__class__ = SplitBodyFeature
                feature.name = "Custom timeline name"
                spec, values = self.updated(record)
                spec["name"] = "Renamed candidate"
                if failure == "metadata":
                    feature.attributes.fail_next = True
                elif failure == "finish":
                    feature.fail_finish = True
                else:
                    def compute_health():
                        feature.healthState = 2 if result_body.shape == "new" else 0
                    self.design.compute_hook = compute_health
                with self.assertRaises(d.DocumentError):
                    d.commit_candidate(self.design, spec, values, Body("new", True), record)
                self.assertEqual(source_body.name, "Different source name")
                self.assertEqual(result_body.name, "Custom result name")
                self.assertEqual(feature.name, "Custom timeline name")
                self.assertEqual(component.name, "Original gear component")
                self.assertEqual(component.placement, {"x": 19, "angle": 0.7})
                self.assertEqual(result_body.shape, "original")
                self.assertEqual(d.find_record(self.design, record.id).spec["name"], record.spec["name"])

    def test_update_from_parameters_reads_current_expression(self):
        record = self.create()
        self.design.userParameters.itemByName(record.parameter_names["teeth"]).expression = "32"
        spec = d.current_spec(self.design, record)
        self.assertEqual(spec["parameters"]["teeth"], "32")
        self.assertEqual(record.spec["parameters"]["teeth"], "24")
        self.assertEqual(d.resolve_spec(self.design, spec, record.parameter_names)["teeth"], 32)

    def test_partial_update_body_failure_restores_original_in_place(self):
        record = self.create()
        spec, values = self.updated(record)
        expressions = {name: parameter.expression for name, parameter in self.design.userParameters.data.items()}
        record.feature.fail_update = True
        with self.assertRaises(d.DocumentError):
            d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assertEqual(record.feature.updates, ["new", "original"])
        self.assert_restored(record, expressions)

    def test_metadata_failure_after_finish_restores_body_and_definition(self):
        record = self.create()
        spec, values = self.updated(record)
        expressions = {name: parameter.expression for name, parameter in self.design.userParameters.data.items()}
        record.feature.attributes.fail_next = True
        with self.assertRaises(d.DocumentError):
            d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assert_restored(record, expressions)

    def test_compute_failure_restores_body_and_parameters(self):
        record = self.create()
        spec, values = self.updated(record)
        expressions = {name: parameter.expression for name, parameter in self.design.userParameters.data.items()}
        self.design.fail_compute_once = True
        with self.assertRaises(d.DocumentError):
            d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assert_restored(record, expressions)

    def test_downstream_failure_rolls_back_source_and_table(self):
        record = self.create()
        downstream = self.design.rootComponent.features.add()
        downstream.name = "Tooth fillet"
        spec, values = self.updated(record)
        expressions = {name: parameter.expression for name, parameter in self.design.userParameters.data.items()}
        def compute_health():
            downstream.healthState = 2 if record.feature.bodies.item(0).shape == "new" else 0
        self.design.compute_hook = compute_health
        with self.assertRaisesRegex(d.DocumentError, "downstream feature"):
            d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assert_restored(record, expressions)
        self.assertEqual(downstream.healthState, 0)

    def test_finish_edit_failure_still_restores_source(self):
        record = self.create()
        spec, values = self.updated(record)
        expressions = {name: parameter.expression for name, parameter in self.design.userParameters.data.items()}
        record.feature.fail_finish = True
        with self.assertRaises(d.DocumentError):
            d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assert_restored(record, expressions)

    def test_parameter_assignment_failure_restores_expressions(self):
        record = self.create()
        spec, values = self.updated(record)
        expressions = {name: parameter.expression for name, parameter in self.design.userParameters.data.items()}
        self.design.userParameters.fail_on = (record.parameter_names["teeth"], "30")
        with self.assertRaises(d.DocumentError):
            d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assert_restored(record, expressions)
        self.assertEqual(record.feature.updates, [])

    def test_parameter_creation_failure_cleans_up_partial_rows(self):
        parameters = self.design.userParameters
        add = parameters.add
        def fail_after_first_row(*args):
            if parameters.count:
                raise RuntimeError("injected parameter creation failure")
            return add(*args)
        with patch.object(parameters, "add", side_effect=fail_after_first_row):
            with self.assertRaisesRegex(d.DocumentError, "writing gear parameters"):
                self.create()
        self.assertEqual(parameters.count, 0)
        self.assertEqual(self.design.rootComponent.features.count, 0)

    def test_start_edit_failure_restores_parameters_before_any_body_change(self):
        record = self.create()
        spec, values = self.updated(record)
        expressions = {name: parameter.expression for name, parameter in self.design.userParameters.data.items()}
        with patch.object(record.feature, "startEdit", return_value=False):
            with self.assertRaisesRegex(d.DocumentError, "enter the gear's source feature"):
                d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assert_restored(record, expressions)
        self.assertEqual(record.feature.updates, [])

    def test_native_body_failure_identifies_stage_and_keeps_exception_cause(self):
        record = self.create()
        spec, values = self.updated(record)
        expressions = {name: parameter.expression for name, parameter in self.design.userParameters.data.items()}
        update = record.feature.updateBody
        native_error = RuntimeError("3 : injected native failure")
        def fail_candidate(source, body):
            if body.shape == "new":
                raise native_error
            return update(source, body)
        with patch.object(record.feature, "updateBody", side_effect=fail_candidate):
            with self.assertRaisesRegex(d.DocumentError, "replacing the source solid") as raised:
                d.commit_candidate(self.design, spec, values, Body("new", True), record)
        self.assertIs(raised.exception.__cause__, native_error)
        self.assert_restored(record, expressions)

    def test_failed_creation_removes_component_body_feature_and_parameter_rows(self):
        self.design.fail_compute_once = True
        with self.assertRaises(d.DocumentError): self.create()
        self.assertEqual(d.records(self.design), [])
        self.assertEqual(self.design.rootComponent.features.count, 0)
        self.assertEqual(self.design.userParameters.count, 0)

    def test_changed_values_during_build_are_rejected_before_mutation(self):
        record = self.create()
        spec, values = self.updated(record)
        values["module"] = 123
        with self.assertRaisesRegex(d.DocumentError, "changed while building"):
            d.commit_candidate(self.design, spec, values, Body("wrong", True), record)
        self.assertEqual(record.feature.updates, [])

    def test_duplicate_identity_does_not_silently_choose_a_gear(self):
        record = self.create()
        copy = self.design.rootComponent.features.add()
        copy.attributes.add(d.ATTRIBUTE_GROUP, d.ATTRIBUTE_NAME, record.feature.attributes.itemByName(d.ATTRIBUTE_GROUP, d.ATTRIBUTE_NAME).value)
        with self.assertRaisesRegex(d.DocumentError, "copied identity"):
            d.find_record(self.design, record.id)

    def test_selection_resolves_faces_and_rejects_ambiguous_part_component(self):
        record = self.create()
        app = SimpleNamespace(activeProduct=self.design, userInterface=SimpleNamespace(activeSelections=Collection([
            SimpleNamespace(entity=SimpleNamespace(body=record.feature.bodies.item(0)))])))
        self.assertEqual(d.selected_record(app).id, record.id)
        self.create()
        app.userInterface.activeSelections = Collection([SimpleNamespace(entity=self.design.rootComponent)])
        with self.assertRaisesRegex(d.DocumentError, "more than one"):
            d.selected_record(app)

    def test_multiple_gears_selection_is_explicitly_ambiguous(self):
        one, two = self.create(), self.create()
        app = SimpleNamespace(activeProduct=self.design, userInterface=SimpleNamespace(activeSelections=Collection([
            SimpleNamespace(entity=one.feature), SimpleNamespace(entity=two.feature)])))
        with self.assertRaisesRegex(d.DocumentError, "Multiple gears"):
            d.selected_record(app)

    def test_unrelated_body_in_same_part_does_not_select_the_gear(self):
        self.create()
        unrelated = Body("box")
        unrelated.parentComponent = self.design.rootComponent
        app = SimpleNamespace(activeProduct=self.design, userInterface=SimpleNamespace(activeSelections=Collection([
            SimpleNamespace(entity=unrelated)])))
        self.assertIsNone(d.selected_record(app))

    def test_missing_parameter_requires_repair_instead_of_reset(self):
        record = self.create()
        self.design.userParameters.itemByName(record.parameter_names["module"]).deleteMe()
        with self.assertRaisesRegex(d.DocumentError, "missing or renamed"):
            d.current_spec(self.design, record)

    def test_unsupported_mode_does_not_change_document(self):
        self.design.designType = 0
        with self.assertRaisesRegex(d.DocumentError, "Capture Design History"):
            self.create()
        self.assertEqual(self.design.designType, 0)
        self.assertEqual(self.design.userParameters.count, 0)


if __name__ == "__main__": unittest.main()
