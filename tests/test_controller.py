"""Lifecycle contract tests with minimal event/document fakes.

These exercise our cancellation, freshness, error-reporting and cleanup logic.
They do not execute Autodesk geometry or certify native Fusion event ordering.
"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit
import uuid

from GearStudio.fusion.document import DocumentError


def load_controller():
    fake_adsk = ModuleType("adsk")
    fake_adsk.__path__ = []
    fake_adsk.core = ModuleType("adsk.core")
    fake_adsk.fusion = ModuleType("adsk.fusion")
    fake_adsk.core.CommandCreatedEventHandler = object
    fake_adsk.core.CommandEventHandler = object
    fake_adsk.core.HTMLEventHandler = object
    fake_adsk.fusion.DesignTypes = SimpleNamespace(ParametricDesignType=1)
    fake_adsk.fusion.Design = SimpleNamespace(cast=lambda item: item)
    fake_adsk.doEvents = mock.Mock()
    path = Path(__file__).resolve().parents[1] / "GearStudio" / "fusion" / "controller.py"
    name = "GearStudio.fusion._controller_contract_tests"
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    with mock.patch.dict(sys.modules, {"adsk": fake_adsk, "adsk.core": fake_adsk.core,
                                       "adsk.fusion": fake_adsk.fusion, name: module}):
        specification.loader.exec_module(module)
    return module, fake_adsk


class Event:
    def __init__(self):
        self.handlers = []

    def add(self, handler):
        self.handlers.append(handler)

    def fire(self, args=None):
        for handler in list(self.handlers):
            handler.notify(args or SimpleNamespace())


class Document:
    def __init__(self, app):
        self.app = app
        self.isValid = True

    def activate(self):
        self.app.activeDocument = self
        return True


class Candidate:
    def __init__(self):
        self.body = object()
        self.cleanup_count = 0

    def cleanup(self):
        self.cleanup_count += 1
        self.body = None


class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, cls.adsk = load_controller()

    def setUp(self):
        module = self.module
        self.adsk.doEvents.reset_mock()
        self.adsk.doEvents.side_effect = None
        self.design = SimpleNamespace(designType=1)
        self.app = SimpleNamespace(activeProduct=self.design)
        self.document = Document(self.app)
        self.app.activeDocument = self.document
        self.command_definition = SimpleNamespace(execute=mock.Mock(return_value=True))
        self.controller = module.Controller.__new__(module.Controller)
        self.controller.app = self.app
        self.controller.ui = SimpleNamespace(
            activeCommand="SelectCommand",
            commandDefinitions=SimpleNamespace(itemById=mock.Mock(return_value=self.command_definition)),
        )
        self.controller.store = mock.Mock()
        self.controller.store.list_presets.return_value = []
        self.controller.handlers = []
        self.controller.controls = []
        self.controller.palette = None
        self.controller.pending = None
        self.controller.busy = False
        self.controller.cancel_requested = False
        self.controller.committing = False
        self.controller.stopping = False
        self.controller.editing_id = None
        self.controller.spec = None
        self.controller.log = mock.Mock()
        self.events = []
        self.controller.send = lambda event, data: self.events.append((event, deepcopy(data)))
        self.spec = module.default_spec()
        self.spec["id"] = str(uuid.uuid4())
        self.values = {"teeth": 24.0, "module": 1.0}
        self.validation = {"valid": True, "issues": [], "metrics": {}, "cost": {}}
        self.controller._resolved = mock.Mock(return_value=(self.design, self.spec, self.values, None, self.validation))
        self.candidate = Candidate()
        self.builder = self.patch("build_candidate", return_value=self.candidate)
        self.resolver = self.patch("resolve_spec", return_value=self.values)
        self.commit = self.patch("commit_candidate", return_value=SimpleNamespace(
            spec=self.spec, parameter_names={key: "GS_owned_" + key for key in self.spec["parameters"]}))

    def patch(self, name, **kwargs):
        patcher = mock.patch.object(self.module, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def begin(self):
        self.controller.begin_build(self.spec)

    def assert_released(self):
        self.assertIsNone(self.controller.pending)
        self.assertFalse(self.controller.busy)
        self.assertFalse(self.controller.committing)
        self.assertEqual(self.candidate.cleanup_count, 1)

    def test_html_response_acknowledgements_are_not_dispatched_or_decoded(self):
        owner = SimpleNamespace(dispatch=mock.Mock(), report_error=mock.Mock())
        handler = self.module._HtmlHandler(owner)
        for payload in ("OK", "", "{}", "[]", None):
            with self.subTest(payload=payload):
                args = SimpleNamespace(action="response", data=payload)
                handler.notify(args)
                self.assertEqual(args.returnData, "OK")
        owner.dispatch.assert_not_called()
        owner.report_error.assert_not_called()

    def test_wrapped_native_commit_error_keeps_traceback_in_log(self):
        try:
            try:
                raise RuntimeError("3 : this is not a parametric design")
            except RuntimeError as native_error:
                raise DocumentError("Fusion failed while writing gear parameters.") from native_error
        except DocumentError as error:
            self.controller.report_error(error, "gs-error")
        self.controller.log.info.assert_not_called()
        self.controller.log.error.assert_called_once()
        logged_traceback = self.controller.log.error.call_args.args[2]
        self.assertIn("RuntimeError: 3 : this is not a parametric design", logged_traceback)
        self.assertIn("DocumentError: Fusion failed while writing gear parameters", logged_traceback)
        self.assertEqual(self.events, [("error", {
            "message": "Fusion failed while writing gear parameters.", "requestId": "gs-error"})])

    def test_validation_rejection_remains_concise(self):
        self.controller.report_error(ValueError("Module must be positive."))
        self.controller.log.info.assert_called_once()
        self.controller.log.error.assert_not_called()
        self.assertEqual(self.events[0][1]["message"], "Module must be positive.")

    def test_html_error_acknowledgement_does_not_create_an_error_loop(self):
        owner = SimpleNamespace(dispatch=mock.Mock(), report_error=mock.Mock())
        handler = self.module._HtmlHandler(owner)
        acknowledgement = SimpleNamespace(action="response", data="OK")
        owner.report_error.side_effect = lambda error: handler.notify(acknowledgement)
        request = SimpleNamespace(action="build", data="invalid JSON")
        handler.notify(request)
        owner.report_error.assert_called_once()
        owner.dispatch.assert_not_called()
        self.assertEqual(request.returnData, "ERROR")
        self.assertEqual(acknowledgement.returnData, "OK")

    def test_html_ready_response_correlates_the_handshake(self):
        self.controller.spec = deepcopy(self.spec)
        args = SimpleNamespace(action="ready", data=json.dumps({"requestId": "gs-1"}))
        self.module._HtmlHandler(self.controller).notify(args)
        self.assertEqual(args.returnData, "OK")
        self.assertEqual(len(self.events), 1)
        event, payload = self.events[0]
        self.assertEqual(event, "state")
        self.assertEqual(payload["host"], "fusion")
        self.assertEqual(payload["requestId"], "gs-1")
        self.builder.assert_not_called()

    def test_html_build_request_reaches_candidate_preparation(self):
        args = SimpleNamespace(action="build", data=json.dumps({"spec": self.spec, "requestId": "gs-2"}))
        self.module._HtmlHandler(self.controller).notify(args)
        self.assertEqual(args.returnData, "OK")
        self.builder.assert_called_once()
        self.command_definition.execute.assert_called_once()
        self.assertIs(self.controller.pending.candidate, self.candidate)
        self.controller._finish_pending()

    def test_parameter_rename_uses_native_command_without_building_geometry(self):
        old_names = {field: "GS_owned_" + field for field in self.spec["parameters"]}
        record = SimpleNamespace(id=self.spec["id"], spec=self.spec, parameter_names=old_names)
        new_names = {field: field.title() + "_G1" for field in self.spec["parameters"]}
        renamed = SimpleNamespace(id=record.id, spec=self.spec, parameter_names=new_names)
        self.controller._require_record = mock.Mock(return_value=record)
        self.controller._selection_summary = mock.Mock(return_value={"id": record.id, "readableParameterNames": True})
        self.patch("current_spec", return_value=self.spec)
        self.patch("find_record", return_value=record)
        rename = self.patch("rename_parameters", return_value=renamed)
        self.controller.dispatch("renameParameters", {})
        self.command_definition.execute.assert_called_once()
        self.assertTrue(self.controller.busy)
        self.assertEqual(self.controller.pending.operation, "renameParameters")
        self.controller._commit_execute(SimpleNamespace())
        rename.assert_called_once_with(self.design, record)
        self.builder.assert_not_called()
        self.commit.assert_not_called()
        self.controller.store.remember_success.assert_not_called()
        result = next(payload for action, payload in self.events if action == "result")
        self.assertEqual(result["renamedAliases"]["GS_owned_teeth"], "Teeth_G1")
        self.assertNotIn("spec", result, "A rename must not replace an unsaved panel draft.")
        self.assertIsNone(self.controller.pending)
        self.assertFalse(self.controller.busy)

    def test_parameter_rename_rejects_an_active_fusion_edit(self):
        self.controller.ui.activeCommand = "SketchLine"
        self.controller.dispatch("renameParameters", {})
        self.command_definition.execute.assert_not_called()
        self.assertIsNone(self.controller.pending)
        self.assertFalse(self.controller.busy)
        self.assertIn("Finish or cancel", self.events[-1][1]["message"])

    def test_start_registers_compatible_ui_ids_and_stop_removes_them(self):
        # Exercise startup through its API boundary. Permissive mocks previously
        # missed Fusion rejecting the dotted command IDs reported on Windows.
        # This conservative subset is our compatibility contract, not an
        # exhaustive claim about all identifiers accepted by every Fusion build.
        definitions, palettes, controls = {}, {}, {}

        def check_identity(identity):
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", identity) is None:
                raise RuntimeError("3 : invalid id")

        def add_definition(identity, name, description, resources):
            check_identity(identity)
            self.assertNotIn(identity, definitions)
            self.assertTrue(Path(resources).is_dir())
            definition = SimpleNamespace(
                id=identity, commandCreated=Event(),
                deleteMe=lambda: definitions.pop(identity),
            )
            definitions[identity] = definition
            return definition

        def add_control(definition):
            control = SimpleNamespace(
                isValid=True, deleteMe=lambda: controls.pop(definition.id),
            )
            controls[definition.id] = control
            return control

        def add_palette(identity, name, url, *options):
            check_identity(identity)
            self.assertTrue(url.startswith("file:"))
            self.assertTrue(urlsplit(url).path.endswith("/ui/index.html"))
            self.assertEqual(parse_qs(urlsplit(url).query)["host"], ["fusion"])
            self.assertFalse(options[0], "Register incomingFromHTML before showing the palette.")
            palette = SimpleNamespace(
                isVisible=True, incomingFromHTML=Event(),
                deleteMe=lambda: palettes.pop(identity),
            )
            palettes[identity] = palette
            return palette

        panel = SimpleNamespace(controls=SimpleNamespace(
            itemById=controls.get, addCommand=add_control,
        ))
        self.controller.ui.commandDefinitions = SimpleNamespace(
            itemById=definitions.get, addButtonDefinition=add_definition,
        )
        self.controller.ui.allToolbarPanels = SimpleNamespace(
            itemById=lambda identity: panel if identity == "SolidCreatePanel" else None,
        )
        self.controller.ui.palettes = SimpleNamespace(itemById=palettes.get, add=add_palette)
        self.controller._log_handler = None
        self.controller.send_state = mock.Mock()

        self.controller.start()

        self.assertEqual(set(definitions), {self.module.OPEN_ID, self.module.COMMIT_ID})
        self.assertEqual(set(controls), {self.module.OPEN_ID})
        self.assertTrue(controls[self.module.OPEN_ID].isPromoted)
        self.assertEqual(set(palettes), {self.module.PALETTE_ID})
        self.assertEqual(len(self.controller.handlers), 3)
        self.assertEqual(len(definitions[self.module.COMMIT_ID].commandCreated.handlers), 1)
        definitions[self.module.OPEN_ID].commandCreated.fire()
        self.controller.send_state.assert_called_once()
        self.assertEqual(len(palettes), 1)

        self.controller.stop()

        self.assertFalse(definitions)
        self.assertFalse(palettes)
        self.assertFalse(controls)
        self.assertFalse(self.controller.handlers)
        self.builder.assert_not_called()

    def test_invalid_input_never_invokes_native_builder(self):
        self.validation["valid"] = False
        self.validation["issues"] = [{"field": "module", "severity": "error", "message": "Module must be positive."}]
        with self.assertRaisesRegex(self.module.StudioError, "Module must be positive"):
            self.begin()
        self.builder.assert_not_called()
        self.commit.assert_not_called()
        self.assertFalse(self.controller.busy)

    def test_active_native_command_never_starts_preparation(self):
        self.controller.ui.activeCommand = "Extrude"
        with self.assertRaisesRegex(self.module.StudioError, "active Fusion command"):
            self.begin()
        self.builder.assert_not_called()
        self.controller._resolved.assert_not_called()

    def test_selection_is_stale_after_external_value_change(self):
        record = SimpleNamespace(spec=deepcopy(self.spec), parameter_names={},
                                 applied_values={"teeth": 24.0, "module": 2.0})
        self.patch("selected_record", return_value=record)
        self.patch("current_spec", return_value=deepcopy(self.spec))
        self.assertTrue(self.controller._selection_summary()["stale"])

    def test_refused_commit_command_releases_prepared_solid(self):
        self.command_definition.execute.return_value = False
        with self.assertRaisesRegex(self.module.StudioError, "did not start"):
            self.begin()
        self.assert_released()
        self.commit.assert_not_called()
        self.controller.store.remember_success.assert_not_called()

    def test_cancel_after_preparation_prevents_commit(self):
        self.begin()
        self.controller.dispatch("cancel", {})
        args = SimpleNamespace(executeFailed=False)
        self.controller._commit_execute(args)
        self.assertTrue(args.executeFailed)
        self.commit.assert_not_called()
        self.controller.store.remember_success.assert_not_called()
        self.assert_released()

    def test_document_switch_at_final_yield_prevents_wrong_document_command(self):
        calls = []
        def change_document():
            calls.append(1)
            if len(calls) == 2:
                self.app.activeDocument = Document(self.app)
        self.adsk.doEvents.side_effect = change_document
        with self.assertRaisesRegex(self.module.StudioError, "active document changed"):
            self.begin()
        self.command_definition.execute.assert_not_called()
        self.commit.assert_not_called()
        self.assert_released()

    def test_document_switch_after_command_scheduled_prevents_commit(self):
        self.begin()
        self.app.activeDocument = Document(self.app)
        args = SimpleNamespace(executeFailed=False)
        self.controller._commit_execute(args)
        self.assertTrue(args.executeFailed)
        self.commit.assert_not_called()
        self.assert_released()

    def test_managed_parameter_edit_during_preparation_is_not_overwritten(self):
        original = deepcopy(self.spec)
        record = SimpleNamespace(spec=original, parameter_names={"teeth": "GS_owned_teeth"})
        self.controller._resolved.return_value = (self.design, self.spec, self.values, record, self.validation)
        self.patch("find_record", return_value=record)
        modified = deepcopy(original)
        modified["parameters"]["teeth"] = "36"
        self.patch("current_spec", side_effect=[original, modified])
        with self.assertRaisesRegex(self.module.StudioError, "expressions changed"):
            self.begin()
        self.commit.assert_not_called()
        self.command_definition.execute.assert_not_called()
        self.assert_released()

    def test_external_parameter_change_before_commit_is_rejected(self):
        self.begin()
        self.resolver.return_value = {"teeth": 24.0, "module": 2.0}
        args = SimpleNamespace(executeFailed=False)
        self.controller._commit_execute(args)
        self.assertTrue(args.executeFailed)
        self.commit.assert_not_called()
        self.assert_released()

    def test_destroy_without_execute_cleans_up_queued_candidate(self):
        self.begin()
        command = SimpleNamespace(execute=Event(), destroy=Event())
        self.controller._commit_created(SimpleNamespace(command=command))
        self.assertEqual(len(self.controller.handlers), 2)
        command.destroy.fire()
        self.assertEqual(self.controller.handlers, [])
        self.commit.assert_not_called()
        self.assert_released()

    def test_preferences_failure_after_geometry_commit_still_reports_success(self):
        self.begin()
        self.controller.store.remember_success.side_effect = OSError("preferences are read only")
        self.controller.store.list_presets.side_effect = OSError("preset read failure")
        args = SimpleNamespace(executeFailed=False)
        self.controller._commit_execute(args)
        self.commit.assert_called_once()
        self.assertFalse(args.executeFailed)
        self.assert_released()
        results = [data for event, data in self.events if event == "result"]
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["ok"])
        self.assertEqual(results[0]["spec"]["id"], self.spec["id"])
        self.assertIn("could not be written", results[0]["message"])
        self.assertEqual([event for event, _ in self.events].count("error"), 0)

    def test_failed_commit_never_updates_remembered_defaults(self):
        self.begin()
        self.commit.side_effect = ValueError("Fusion rejected the candidate")
        args = SimpleNamespace(executeFailed=False)
        self.controller._commit_execute(args)
        self.assertTrue(args.executeFailed)
        self.controller.store.remember_success.assert_not_called()
        self.assert_released()

    def test_stopping_remains_cancelled_after_cleanup(self):
        self.begin()
        self.controller.stopping = True
        args = SimpleNamespace(executeFailed=False)
        self.controller._commit_execute(args)
        self.commit.assert_not_called()
        self.assert_released()
        self.assertTrue(self.controller.cancel_requested)

    def test_validation_result_keeps_request_id_on_expression_failure(self):
        self.controller._resolved.side_effect = ValueError("Unknown parameter shaft")
        self.controller.validate_for_ui(self.spec, "request-17")
        event, data = self.events[-1]
        self.assertEqual(event, "validation")
        self.assertEqual(data["requestId"], "request-17")
        self.assertFalse(data["valid"])
        self.builder.assert_not_called()

    def test_success_remembers_independent_template_without_changing_document_definition(self):
        self.spec["parameters"]["module"] = "SharedModule"
        self.spec["parameters"]["width"] = "GS_owned_module * 10"
        self.begin()
        args = SimpleNamespace(executeFailed=False)
        self.controller._commit_execute(args)
        remembered = self.controller.store.remember_success.call_args.args[0]
        self.assertNotIn("id", remembered)
        self.assertEqual(remembered["parameters"]["width"], "(SharedModule) * 10")
        self.assertEqual(self.controller.spec["parameters"]["width"], "GS_owned_module * 10")
        self.assertEqual(self.controller.spec["id"], self.spec["id"])
        self.assertFalse(args.executeFailed)

    def test_duplicate_does_not_link_new_inputs_to_source_owned_parameters(self):
        source = deepcopy(self.spec)
        source["parameters"]["module"] = "ExternalModule"
        source["parameters"]["width"] = "GS_source_module * 8"
        record = SimpleNamespace(spec=source, parameter_names={"module": "GS_source_module"})
        self.controller._require_record = mock.Mock(return_value=record)
        self.controller.send_state = mock.Mock()
        self.patch("current_spec", return_value=source)
        self.controller.use_selected("duplicateSelected")
        duplicate = self.controller.send_state.call_args.args[0]
        self.assertNotIn("id", duplicate)
        self.assertEqual(duplicate["parameters"]["width"], "(ExternalModule) * 8")
        self.assertEqual(source["parameters"]["width"], "GS_source_module * 8")

    def test_saved_preset_detaches_owned_aliases_after_validation(self):
        source = deepcopy(self.spec)
        source["parameters"]["module"] = "ExternalModule"
        source["parameters"]["width"] = "GS_source_module * 8"
        record = SimpleNamespace(spec=source, parameter_names={"module": "GS_source_module"})
        self.controller._resolved.return_value = (self.design, source, self.values, record, self.validation)
        self.controller.save_preset({"name": "Reusable", "spec": source})
        name, saved = self.controller.store.save_preset.call_args.args
        self.assertEqual(name, "Reusable")
        self.assertNotIn("id", saved)
        self.assertEqual(saved["parameters"]["width"], "(ExternalModule) * 8")


if __name__ == "__main__":
    unittest.main()
