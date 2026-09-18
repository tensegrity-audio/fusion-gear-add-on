"""Construction ownership/transaction boundary tests, not Fusion kernel tests."""
from copy import deepcopy
from types import SimpleNamespace, ModuleType
import sys
import unittest
from unittest.mock import patch

from test_document import Design, Collection, Attributes, API, Body
from GearStudio.core.catalog import default_spec
from GearStudio.fusion import history as h, document as d


class Items(Collection):
    def __iter__(self): return iter(self.items)


class Features(Items):
    @property
    def baseFeatures(self): return Items()


class Occurrences(Items):
    def __init__(self, owner): super().__init__(); self.owner = owner
    def addNewComponent(self, matrix):
        design = self.owner.design
        component = Component(design)
        result = SimpleNamespace(component=component, attributes=Attributes(), isValid=True, transform2=matrix)
        def delete():
            result.isValid = False
            for child in list(h._components(component)):
                for feature in child.features:
                    feature.isValid = False
                design.allComponents.items.remove(child)
            self.items.remove(result)
            return True
        result.deleteMe = delete
        self.items.append(result)
        design.timeline.count += 1
        design.timeline.markerPosition = design.timeline.count
        return result


class Component:
    def __init__(self, design):
        self.design = design
        self.attributes = Attributes()
        self.features = Features()
        self.sketches = Items()
        self.bRepBodies = Items()
        self.occurrences = Occurrences(self)
        self.isValid = True
        self.name = 'Component'
        design.allComponents.items.append(self)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.design = Design()
        self.design.designIntent = 2
        self.design.allComponents = Items()
        self.design.rootComponent = Component(self.design)
        self.groups = []
        def add_group(first, last):
            group = SimpleNamespace(first=first, last=last)
            self.groups.append(group)
            return group
        self.design.timeline = SimpleNamespace(markerPosition=0, count=0, timelineGroups=SimpleNamespace(add=add_group))
        self.design.activateRootComponent = lambda: True
        self.core = SimpleNamespace(**vars(API[0]))
        self.core.Matrix3D = SimpleNamespace(create=lambda: object())
        self.fusion = SimpleNamespace(**vars(API[1]))
        self.spec = default_spec('helical')
        self.candidate = Body('checked', True)
        self.candidate.faces = Items([1]); self.candidate.volume = 1
        self.api = patch.object(d, '_api', return_value=(self.core, self.fusion))
        self.api.start(); self.addCleanup(self.api.stop)
        self.adsk = patch.dict(sys.modules, {'adsk': ModuleType('adsk')})
        self.adsk.start(); self.addCleanup(self.adsk.stop)
        self.generator = patch.object(h, 'generate_native', side_effect=self.generate)
        self.generator.start(); self.addCleanup(self.generator.stop)
        self.values = d.resolve_spec(self.design, self.spec)

    def generate(self, parent, kind, values, adsk, parameter_names=None):
        self.last_parameter_names = dict(parameter_names)
        body = deepcopy(self.candidate)
        body.parentComponent = parent
        parent.bRepBodies.items.append(body)
        parent.features.items.append(SimpleNamespace(parentComponent=parent, isValid=True, healthState=0, editing=False))
        self.design.timeline.count += 3
        self.design.timeline.markerPosition = self.design.timeline.count
        return body

    def create(self):
        return h.commit_history(self.design, self.spec, self.values, self.candidate)

    def test_new_gear_owns_native_history_and_can_be_selected_by_body(self):
        record = self.create()
        self.assertEqual(record.construction, 'native_history')
        self.assertEqual(d.records(self.design)[0].construction, 'native_history')
        self.assertEqual(sum(c.features.baseFeatures.count for c in self.design.allComponents), 0)
        self.assertTrue(record.component.isSketchFolderLightBulbOn)
        self.assertFalse(self.groups[0].isCollapsed)
        self.assertEqual(self.last_parameter_names, record.parameter_names)
        outer = self.design.rootComponent.occurrences.item(0)
        self.assertFalse(outer.isGroundToParent)
        self.assertTrue(h._generation(record).isGroundToParent)
        app = SimpleNamespace(activeProduct=self.design, userInterface=SimpleNamespace(
            activeSelections=Items([SimpleNamespace(entity=record.bodies[0])])) )
        self.assertEqual(d.selected_record(app).id, record.id)
        leaf = h._generation(record)
        app.userInterface.activeSelections = Items([SimpleNamespace(entity=leaf)])
        self.assertEqual(d.selected_record(app).id, record.id)

    def test_update_retains_outer_component_and_placement(self):
        record = self.create()
        occurrence = self.design.rootComponent.occurrences.item(0)
        placement = object(); occurrence.transform2 = placement
        previous = h._generation(record)
        spec = deepcopy(record.spec); spec['parameters']['teeth'] = '32'
        values = d.resolve_spec(self.design, spec, record.parameter_names)
        updated = h.commit_history(self.design, spec, values, self.candidate, record)
        self.assertIs(updated.component, record.component)
        self.assertIs(occurrence.transform2, placement)
        self.assertFalse(previous.isValid)
        self.assertEqual(updated.parameter_names, record.parameter_names)
        self.assertEqual(len(d.records(self.design)), 1)
        self.assertEqual(updated.applied_values['teeth'], 32)
        self.assertFalse(occurrence.isGroundToParent)

    def test_old_bore_is_frozen_before_user_inputs_change_and_new_build_keeps_binding(self):
        record = self.create()
        previous = h._generation(record)
        diameter = SimpleNamespace(parameter=SimpleNamespace(expression=record.parameter_names['bore']),
                                   attributes=Attributes())
        diameter.attributes.add(d.ATTRIBUTE_GROUP, h.DIAMETER_INPUT, 'bore')
        unrelated = SimpleNamespace(parameter=SimpleNamespace(expression='shaftDiameter'), attributes=Attributes())
        previous.component.sketches.items.append(SimpleNamespace(sketchDimensions=Items([diameter, unrelated])))
        external = SimpleNamespace(parameter=SimpleNamespace(expression=record.parameter_names['bore']), attributes=Attributes())
        external.attributes.add(d.ATTRIBUTE_GROUP, h.DIAMETER_INPUT, 'bore')
        self.design.rootComponent.sketches.items.append(SimpleNamespace(
            sketchDimensions=Items([external]), isValid=True))
        spec = deepcopy(record.spec)
        spec['parameters']['module'] = '2 mm'
        spec['parameters']['bore'] = '30 mm'
        values = d.resolve_spec(self.design, spec, record.parameter_names)
        apply = d._apply_parameters
        def assert_old_size(*args, **kwargs):
            self.assertAlmostEqual(self.design.unitsManager.evaluateExpression(diameter.parameter.expression, 'mm'), .5)
            self.assertNotIn(record.parameter_names['bore'], diameter.parameter.expression)
            self.assertEqual(unrelated.parameter.expression, 'shaftDiameter')
            self.assertEqual(external.parameter.expression, record.parameter_names['bore'])
            return apply(*args, **kwargs)
        with patch.object(d, '_apply_parameters', side_effect=assert_old_size):
            updated = h.commit_history(self.design, spec, values, self.candidate, record)
        self.assertEqual(self.last_parameter_names, record.parameter_names)
        self.assertEqual(updated.applied_values['bore'], 30)

    def test_failed_dimension_detach_aborts_before_parameter_mutation(self):
        record = self.create(); previous = h._generation(record)
        class RefusingParameter:
            @property
            def expression(self): return record.parameter_names['bore']
            @expression.setter
            def expression(self, value): raise RuntimeError('diameter cannot be edited')
        dimension = SimpleNamespace(parameter=RefusingParameter(), attributes=Attributes())
        dimension.attributes.add(d.ATTRIBUTE_GROUP, h.DIAMETER_INPUT, 'bore')
        previous.component.sketches.items.append(SimpleNamespace(sketchDimensions=Items([dimension])))
        with patch.object(d, '_apply_parameters') as apply:
            with self.assertRaisesRegex(d.DocumentError, 'rolled back.*diameter cannot be edited'):
                h.commit_history(self.design, record.spec, self.values, self.candidate, record)
            apply.assert_not_called()
        self.assertTrue(previous.isValid)

    def test_failed_staged_build_keeps_old_generation_until_command_abort(self):
        record = self.create(); previous = h._generation(record)
        with patch.object(h, 'generate_native', side_effect=RuntimeError('loft failed')):
            with self.assertRaisesRegex(d.DocumentError, 'rolled back.*loft failed'):
                h.commit_history(self.design, record.spec, self.values, self.candidate, record)
        self.assertTrue(previous.isValid)
        self.assertEqual(d.find_record(self.design, record.id).spec, record.spec)

    def test_cascaded_external_deletion_requires_transaction_abort(self):
        record = self.create(); previous = h._generation(record)
        dependent = SimpleNamespace(parentComponent=self.design.rootComponent, isValid=True, healthState=0, editing=False)
        self.design.rootComponent.features.items.append(dependent)
        delete = previous.deleteMe
        def cascade():
            dependent.isValid = False
            return delete()
        previous.deleteMe = cascade
        with self.assertRaisesRegex(d.DocumentError, 'outside this gear'):
            h.commit_history(self.design, record.spec, self.values, self.candidate, record)

    def test_part_design_rejected_before_any_parameters_or_occurrences(self):
        self.design.designIntent = 0
        with self.assertRaisesRegex(d.DocumentError, 'Hybrid'):
            self.create()
        self.assertEqual(self.design.userParameters.count, 0)
        self.assertEqual(self.design.rootComponent.occurrences.count, 0)

    def test_rolled_back_timeline_is_rejected_before_work(self):
        self.design.timeline.count = 5
        with self.assertRaisesRegex(d.DocumentError, 'timeline marker'):
            self.create()
        self.assertEqual(self.design.userParameters.count, 0)


if __name__ == '__main__': unittest.main()
