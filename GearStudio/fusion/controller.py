"""Palette, Fusion commands, and the validate/prepare/commit lifecycle.

The solid is prepared before entering the commit command. The command provides
one native undo operation; document.py owns restoration if committing fails.
Nothing in a field-change event creates native geometry.
"""

from copy import deepcopy
from dataclasses import dataclass
import json
import logging
from logging.handlers import RotatingFileHandler
import math
from pathlib import Path
import re
import traceback
import uuid

import adsk
import adsk.core
import adsk.fusion

from ..core.catalog import catalog, default_spec
from .. import __version__
from ..core.storage import SettingsStore
from ..core.validation import validate
from ..core.profiles import preview
from .builder import build_candidate, SUPPORTED_KINDS
from .document import (
    resolve_spec, records, find_record, selected_record, current_spec,
    commit_candidate, rename_parameters, readable_parameter_names,
)


# Keep Fusion UI identifiers to ASCII letters, digits and underscores. The
# dotted command IDs used in 0.1.0 were rejected with "3 : invalid id" on Windows.
# These UI IDs are unrelated to persisted gear identities and parameter names.
PALETTE_ID = "griffin_gearstudio_palette_v1"
OPEN_ID = "griffin_gearstudio_open_v1"
COMMIT_ID = "griffin_gearstudio_commit_v1"
MAX_MESSAGE_BYTES = 65536


class StudioError(ValueError):
    pass


class Cancelled(StudioError):
    pass


@dataclass
class PendingBuild:
    document: object
    design: object
    spec: dict
    values: dict
    record: object
    original_definition: str
    original_expressions: str
    candidate: object = None
    operation: str = "build"


def _fingerprint(spec):
    return json.dumps(spec, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _same_values(first, second):
    return first.keys() == second.keys() and all(
        math.isclose(float(first[key]), float(second[key]), rel_tol=1e-11, abs_tol=1e-10)
        for key in first
    )


def _normalise_spec(raw):
    if not isinstance(raw, dict):
        raise StudioError("Choose a gear type and enter its settings.")
    kind = raw.get("kind", "spur")
    if kind not in SUPPORTED_KINDS:
        raise StudioError("This gear type is not supported by this installed version.")
    spec = default_spec(kind)
    name = raw.get("name", spec.get("name", "Gear"))
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        raise StudioError("Use a gear name between 1 and 80 characters.")
    if any(ord(char) < 32 for char in name):
        raise StudioError("The gear name cannot contain control characters.")
    spec["name"] = name.strip()
    supplied = raw.get("parameters", {})
    if not isinstance(supplied, dict):
        raise StudioError("Gear parameters must be named expressions.")
    allowed = set(spec["parameters"])
    for key, value in supplied.items():
        if key not in allowed:
            continue
        if not isinstance(value, str):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                value = str(value)
            else:
                raise StudioError("Enter a number or an expression for " + key.replace("_", " ") + ".")
        if not value.strip() or len(value) > 256:
            raise StudioError("Each parameter needs an expression of at most 256 characters.")
        spec["parameters"][key] = value.strip()
    identity = raw.get("id")
    if identity:
        try:
            spec["id"] = str(uuid.UUID(str(identity)))
        except ValueError as exc:
            raise StudioError("The saved gear identity is invalid. Duplicate the gear to create a new definition.") from exc
    else:
        spec.pop("id", None)
    spec["schema_version"] = 1
    # Placement of an existing component belongs to Fusion, not to form data.
    spec["placement"] = deepcopy(raw.get("placement", {})) if isinstance(raw.get("placement", {}), dict) else {}
    return spec


class _CommandCreated(adsk.core.CommandCreatedEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def notify(self, args):
        self.callback(args)


class _CommandExecute(adsk.core.CommandEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def notify(self, args):
        self.callback(args)


class _HtmlHandler(adsk.core.HTMLEventHandler):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def notify(self, args):
        # Qt sends an acknowledgement when sendInfoToHTML returns. Its payload
        # is not a Gear Studio request (it may just be "OK"). Reporting an error
        # here would itself produce another acknowledgement and error loop.
        if args.action == "response":
            args.returnData = "OK"
            return
        try:
            if len(args.data.encode("utf-8")) > MAX_MESSAGE_BYTES:
                raise StudioError("The request is too large. Shorten the parameter expressions.")
            data = json.loads(args.data or "{}")
            if not isinstance(data, dict):
                raise StudioError("The request must contain named settings.")
            self.owner.dispatch(args.action, data)
            args.returnData = "OK"
        except Exception as exc:
            self.owner.report_error(exc)
            args.returnData = "ERROR"


class Controller:
    def __init__(self):
        self.app = adsk.core.Application.get()
        self.ui = self.app.userInterface
        self.store = SettingsStore()
        self.handlers = []
        self.controls = []
        self.palette = None
        self.pending = None
        self.busy = False
        self.cancel_requested = False
        self.committing = False
        self.stopping = False
        self.editing_id = None
        self.spec = None
        self.log = logging.getLogger("GearStudio")
        self.log.setLevel(logging.INFO)
        self._log_handler = None
        try:
            path = Path(self.store.path).parent / "GearStudio.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(str(path), maxBytes=1024 * 1024, backupCount=2, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.log.addHandler(handler)
            self._log_handler = handler
        except Exception:
            pass

    def start(self):
        self.store.load()
        self._register_command(OPEN_ID, "Gear Studio", "Create and edit validated B-rep gears", self._open_created)
        self._register_command(COMMIT_ID, "Update Gear Studio solid", "Commit prepared gear geometry", self._commit_created)
        # The palette opens immediately even if a Fusion release changes panel IDs.
        for panel_id in ("SolidCreatePanel", "AssemblyInsertPanel", "AssemblyCreatePanel"):
            panel = self.ui.allToolbarPanels.itemById(panel_id)
            if panel is None:
                continue
            existing = panel.controls.itemById(OPEN_ID)
            if existing:
                existing.deleteMe()
            control = panel.controls.addCommand(self.ui.commandDefinitions.itemById(OPEN_ID))
            control.isPromoted = True
            self.controls.append(control)
        self.open_palette()

    def _register_command(self, identity, name, description, callback):
        definition = self.ui.commandDefinitions.itemById(identity)
        if definition:
            definition.deleteMe()
        resources = str(Path(__file__).resolve().parents[1] / "resources")
        definition = self.ui.commandDefinitions.addButtonDefinition(identity, name, description, resources)
        handler = _CommandCreated(callback)
        definition.commandCreated.add(handler)
        self.handlers.append(handler)

    def _open_created(self, args):
        try:
            self.open_palette()
        except Exception as exc:
            self.report_error(exc)

    def open_palette(self):
        existing = self.ui.palettes.itemById(PALETTE_ID)
        if existing:
            self.palette = existing
            self.palette.isVisible = True
            self.send_state()
            return
        url = (Path(__file__).resolve().parents[1] / "ui" / "index.html").as_uri()
        url += "?host=fusion"
        self.palette = self.ui.palettes.add(PALETTE_ID, "Gear Studio", url, False, True, True, 1160, 800, True)
        handler = _HtmlHandler(self)
        self.palette.incomingFromHTML.add(handler)
        self.handlers.append(handler)
        self.palette.isVisible = True

    def design(self):
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if design is None and self.app.activeDocument:
            try:
                design = adsk.fusion.Design.cast(self.app.activeDocument.products.itemByProductType("DesignProductType"))
            except Exception:
                pass
        if design is None:
            raise StudioError("Open a Fusion design before creating or editing a gear.")
        return design

    def _require_history(self, design):
        if design.designType != adsk.fusion.DesignTypes.ParametricDesignType:
            raise StudioError("Editable gears need design history. Enable Capture Design History in Fusion, then try again.")
        intents = getattr(adsk.fusion, "DesignIntentTypes", None)
        if intents is not None and getattr(design, "designIntent", None) == intents.AssemblyDesignIntentType:
            raise StudioError("Open a Part or Hybrid design to create gear solids. This document is an Assembly design.")
        if getattr(getattr(design, "parentDocument", None), "isReadOnly", False):
            raise StudioError("This design is read-only. Open an editable copy before building a gear.")

    def _get_default(self, kind="spur"):
        remembered = self.store.last_spec(kind)
        spec = remembered if remembered else default_spec(kind)
        spec.pop("id", None)
        return _normalise_spec(spec)

    def _selection_summary(self):
        try:
            record = selected_record(self.app)
            if record:
                design = self.design()
                active = current_spec(design, record)
                stale = active.get("parameters", {}) != record.spec.get("parameters", {})
                try:
                    values = resolve_spec(design, active, record.parameter_names)
                    stale = stale or not _same_values(values, record.applied_values)
                except Exception:
                    stale = True
                return {"id": record.spec["id"], "name": record.spec["name"], "stale": stale,
                        "readableParameterNames": readable_parameter_names(record),
                        "parameterNames": record.parameter_names}
        except Exception:
            return None
        return None

    def send_state(self, spec=None, request_id=None):
        if spec is not None:
            self.spec = deepcopy(spec)
        if self.spec is None:
            state = self.store.load()
            kind = state.get("last_kind", "spur")
            if kind not in SUPPORTED_KINDS:
                kind = "spur"
            self.spec = self._get_default(kind)
        payload = {
            "catalog": catalog(), "spec": self.spec,
            "presets": self.safe_presets(), "selection": self._selection_summary(),
            "mode": "edit" if self.spec.get("id") else "create",
            "supportedKinds": sorted(SUPPORTED_KINDS), "host": "fusion",
            "version": __version__, "installationPath": str(Path(__file__).resolve().parents[1]),
        }
        if self.spec.get("id"):
            try:
                payload["parameterNames"] = find_record(self.design(), self.spec["id"]).parameter_names
            except ValueError:
                # Validation reports missing/deleted definitions; opening help
                # and the palette must still work without a resolvable gear.
                payload["parameterNames"] = {}
        if request_id is not None:
            payload["requestId"] = request_id
        self.send("state", payload)

    def safe_presets(self):
        try:
            return self.store.list_presets()
        except Exception:
            self.log.exception("Could not read saved presets")
            return []

    def send(self, action, data):
        if self.palette:
            try:
                self.palette.sendInfoToHTML(action, json.dumps(data, ensure_ascii=False, allow_nan=False))
            except Exception:
                self.log.warning("Could not send palette event %s", action)

    def report_error(self, exc, request_id=None):
        expected = isinstance(exc, (ValueError, Cancelled))
        # DocumentError wraps native commit errors with recovery guidance. Keep
        # their chained traceback in the log instead of treating them as plain
        # validation rejections and losing the failing Fusion API call.
        if expected and exc.__cause__ is None:
            self.log.info("Request rejected: %s", exc)
        else:
            self.log.error("Gear Studio error: %s\n%s", exc, traceback.format_exc())
        message = str(exc) or "Fusion could not complete this operation. Your previous gear has been retained."
        payload = {"message": message, "requestId": request_id}
        if not expected:
            payload["details"] = traceback.format_exc()
        self.send("error", payload)

    def dispatch(self, action, data):
        request_id = data.get("requestId")
        if action == "cancel":
            if self.busy and not self.committing:
                self.cancel_requested = True
                self.send("progress", {"message": "Cancelling at the next safe checkpoint…", "percent": 0, "cancellable": False})
            return
        if self.busy:
            if action not in ("validate", "refreshSelection"):
                self.send("error", {"message": "Wait for the current gear build to finish or cancel it.", "requestId": request_id})
            return
        try:
            if action == "ready":
                self.send_state(request_id=request_id)
            elif action == "validate":
                self.validate_for_ui(data.get("spec"), request_id)
            elif action == "build":
                self.begin_build(data.get("spec"))
            elif action == "renameParameters":
                self.begin_parameter_rename()
            elif action in ("editSelected", "duplicateSelected", "updateSelected"):
                self.use_selected(action)
            elif action == "loadLast":
                self.editing_id = None
                self.send_state(self._get_default(data.get("kind", "spur")))
            elif action == "refreshSelection":
                self.send("selection", self._selection_summary())
            elif action == "savePreset":
                self.save_preset(data)
            elif action == "loadPreset":
                self.load_preset(data.get("id"))
            elif action == "deletePreset":
                self.store.delete_preset(data.get("id"))
                self.send("result", {"ok": True, "message": "Preset deleted.", "presets": self.store.list_presets()})
            elif action == "openParameters":
                self.open_parameters()
            else:
                self.log.warning("Unsupported palette action: %r", str(action)[:80])
                raise StudioError("Unsupported Gear Studio panel action: " + repr(str(action)[:80])
                                  + ". Stop and restart the add-in after updating its files.")
        except Exception as exc:
            self.report_error(exc, request_id)

    def _resolved(self, raw):
        spec = _normalise_spec(raw)
        design = self.design()
        record = find_record(design, spec["id"]) if spec.get("id") else None
        if spec.get("id") and record is None:
            raise StudioError("This gear is not in the active document. Select it in its original document or create a new gear.")
        values = resolve_spec(design, spec, record.parameter_names if record else None)
        result = validate(spec, values)
        return design, spec, values, record, result

    def validate_for_ui(self, raw, request_id):
        try:
            design, spec, values, record, result = self._resolved(raw)
            result["requestId"] = request_id
            result["preview"] = None
            if result["valid"]:
                try:
                    result["preview"] = preview(spec, values)
                except Exception:
                    self.log.exception("Lightweight preview unavailable for %s", spec["kind"])
                    result.setdefault("issues", []).append({"field": "", "code": "preview_unavailable", "severity": "warning", "message": "The cross-section preview is unavailable for these settings."})
            self.send("validation", result)
        except Exception as exc:
            self.send("validation", {
                "requestId": request_id, "valid": False,
                "issues": [{"field": getattr(exc, "field", ""), "code": "expression", "severity": "error", "message": str(exc)}],
                "metrics": {}, "cost": {}, "preview": None,
            })

    def _require_record(self):
        record = selected_record(self.app)
        if record is None and self.editing_id:
            record = find_record(self.design(), self.editing_id)
        if record is None:
            raise StudioError("Select a Gear Studio body or component in Fusion first.")
        return record

    def use_selected(self, action):
        from ..core.templates import template_spec
        design = self.design()
        record = self._require_record()
        spec = current_spec(design, record)
        if action == "duplicateSelected":
            spec = template_spec(spec, record.parameter_names)
            spec["name"] = (spec["name"][:70] + " copy")
            spec["placement"] = {}
            self.editing_id = None
            self.send_state(spec)
        elif action == "editSelected":
            self.editing_id = spec["id"]
            self.send_state(spec)
        else:
            self.editing_id = spec["id"]
            self.send_state(spec)
            self.begin_build(spec)

    def save_preset(self, data):
        from ..core.templates import template_spec
        design, spec, values, record, result = self._resolved(data.get("spec"))
        if not result["valid"]:
            raise StudioError("Correct the highlighted settings before saving this preset.")
        item = self.store.save_preset(data.get("name", ""), template_spec(spec, record.parameter_names if record else None))
        self.send("result", {"ok": True, "message": "Preset saved.", "presets": self.store.list_presets()})

    def load_preset(self, identity):
        for preset in self.store.list_presets():
            if preset["id"] == identity:
                spec = deepcopy(preset["spec"])
                spec.pop("id", None)
                self.editing_id = None
                self.send_state(_normalise_spec(spec))
                return
        raise StudioError("That preset no longer exists. Refresh the preset list and try again.")

    def open_parameters(self):
        for identity in ("ChangeParameterCommand", "ChangeParametersCommand", "ParametersCommand"):
            command = self.ui.commandDefinitions.itemById(identity)
            if command:
                command.execute()
                return
        raise StudioError("Open Modify > Change Parameters in Fusion, then use Update from Parameters in Gear Studio.")

    def progress(self, message, percent=0):
        if self.cancel_requested or self.stopping:
            raise Cancelled("Build cancelled. The previous gear and saved defaults were retained.")
        self.send("progress", {"message": str(message), "percent": max(0, min(98, float(percent))), "cancellable": not self.committing})
        if not self.committing:
            adsk.doEvents()
        if self.cancel_requested or self.stopping:
            raise Cancelled("Build cancelled. The previous gear and saved defaults were retained.")

    def begin_build(self, raw):
        if getattr(self.ui, "activeCommand", "") not in ("", "SelectCommand"):
            raise StudioError("Finish or cancel the active Fusion command before building a gear.")
        design, spec, values, record, validation = self._resolved(raw)
        self._require_history(design)
        if not validation["valid"]:
            validation["preview"] = None
            self.send("validation", validation)
            messages = [issue["message"] for issue in validation["issues"] if issue["severity"] == "error"]
            raise StudioError("Cannot build this gear. " + " ".join(messages[:3]))
        if not spec.get("id"):
            spec["id"] = str(uuid.uuid4())
        pending = PendingBuild(
            self.app.activeDocument, design, deepcopy(spec), deepcopy(values), record,
            _fingerprint(record.spec) if record else "",
            _fingerprint(current_spec(design, record).get("parameters", {})) if record else "",
        )
        self.pending = pending
        self.busy = True
        self.cancel_requested = False
        try:
            self.progress("Preparing a validated B-rep solid…", 3)
            pending.candidate = build_candidate(spec, values, progress=self.progress, cancelled=lambda: self.cancel_requested or self.stopping)
            if self.cancel_requested:
                raise Cancelled("Build cancelled. The previous gear and saved defaults were retained.")
            pending.document.activate()
            self._check_pending(pending)
            self.progress("Solid prepared. Applying the gear definition…", 96)
            self._check_pending(pending)
            command = self.ui.commandDefinitions.itemById(COMMIT_ID)
            if command is None:
                raise StudioError("Gear Studio's update command is unavailable. Restart the add-in and try again.")
            if command.execute() is False:
                raise StudioError("Fusion did not start the gear update command. The prepared solid was discarded; try again.")
        except Exception:
            self._finish_pending()
            raise

    def begin_parameter_rename(self):
        if getattr(self.ui, "activeCommand", "") not in ("", "SelectCommand"):
            raise StudioError("Finish or cancel the active Fusion command before renaming parameters.")
        design = self.design()
        self._require_history(design)
        record = self._require_record()
        spec = current_spec(design, record)
        self.pending = PendingBuild(
            self.app.activeDocument, design, spec, resolve_spec(design, spec, record.parameter_names), record,
            _fingerprint(record.spec), _fingerprint(spec["parameters"]), operation="renameParameters",
        )
        self.busy = True
        self.cancel_requested = False
        try:
            self.send("progress", {"message": "Renaming the selected gear's parameters…", "percent": 50, "cancellable": False})
            command = self.ui.commandDefinitions.itemById(COMMIT_ID)
            if command is None or command.execute() is False:
                raise StudioError("Fusion did not start the parameter update command. Restart the add-in and try again.")
        except Exception:
            self._finish_pending()
            raise

    def _check_pending(self, pending):
        if self.cancel_requested or self.stopping:
            raise Cancelled("Build cancelled. The previous gear and saved defaults were retained.")
        if hasattr(pending.document, "isValid") and not pending.document.isValid:
            raise StudioError("The original document was closed. The generated candidate has been discarded.")
        if self.app.activeDocument != pending.document:
            raise StudioError("The active document changed before the update. Return to the original design and try again.")
        if pending.record:
            live = find_record(pending.design, pending.spec["id"])
            if live is None or _fingerprint(live.spec) != pending.original_definition:
                raise StudioError("The gear changed while the new solid was being prepared. Reload it and try again.")
            if _fingerprint(current_spec(pending.design, live).get("parameters", {})) != pending.original_expressions:
                raise StudioError("The gear's parameter expressions changed during preparation. Reload it before updating.")
            pending.record = live
        latest = resolve_spec(pending.design, pending.spec, pending.record.parameter_names if pending.record else None)
        if not _same_values(latest, pending.values):
            raise StudioError("A referenced parameter changed during the build. Review the updated values and build again.")

    def _commit_created(self, args):
        pending = self.pending
        handler = _CommandExecute(self._commit_execute)
        args.command.execute.add(handler)
        self.handlers.append(handler)
        def on_destroy(event_args):
            if pending is not None and self.pending is pending and not self.committing:
                message = ("The parameter rename command ended before applying the new names."
                           if pending.operation == "renameParameters"
                           else "The gear update command ended before applying the prepared solid.")
                self.report_error(Cancelled(message))
                self._finish_pending()
            for owned in (handler, destroy):
                if owned in self.handlers:
                    self.handlers.remove(owned)
        destroy = _CommandExecute(on_destroy)
        args.command.destroy.add(destroy)
        self.handlers.append(destroy)
        try:
            args.command.isAutoExecute = True
            args.command.isRepeatable = False
        except Exception:
            pass

    def _commit_execute(self, args):
        from ..core.templates import template_spec
        pending = self.pending
        if pending is None:
            return
        self.committing = True
        try:
            self._check_pending(pending)
            if pending.operation == "renameParameters":
                previous = pending.record.parameter_names
                record = rename_parameters(pending.design, pending.record)
                self.spec = current_spec(pending.design, record)
                self.editing_id = record.id
                self.send("result", {
                    "ok": True, "message": "Parameter names shortened. Gear geometry is unchanged.",
                    "renamedAliases": {previous[field]: name for field, name in record.parameter_names.items()},
                    "gearId": record.id, "parameterNames": record.parameter_names,
                    "selection": self._selection_summary(),
                })
                return
            record = commit_candidate(pending.design, pending.spec, pending.values, pending.candidate.body, pending.record)
            self.spec = deepcopy(record.spec)
            self.editing_id = self.spec["id"]
            message = "Gear updated." if pending.record else "Gear created."
            try:
                self.store.remember_success(template_spec(self.spec, record.parameter_names))
            except Exception:
                self.log.exception("Gear committed, but preferences could not be saved")
                message += " The gear is saved in this design; last-used settings could not be written."
            self.send("progress", {"message": message, "percent": 100, "cancellable": False})
            self.send("result", {"ok": True, "message": message, "spec": self.spec, "mode": "edit", "presets": self.safe_presets(),
                                 "parameterNames": record.parameter_names})
        except Exception as exc:
            try:
                args.executeFailed = True
                args.executeFailedMessage = str(exc)
            except Exception:
                pass
            self.report_error(exc)
        finally:
            self._finish_pending()

    def _finish_pending(self):
        pending = self.pending
        self.pending = None
        self.committing = False
        self.busy = False
        self.cancel_requested = self.stopping
        if pending and pending.candidate:
            try:
                pending.candidate.cleanup()
            except Exception:
                self.log.exception("Candidate cleanup failed")

    def stop(self):
        self.stopping = True
        self.cancel_requested = True
        if not self.busy:
            self._finish_pending()
        for control in self.controls:
            try:
                if control.isValid:
                    control.deleteMe()
            except Exception:
                pass
        self.controls.clear()
        palette = self.ui.palettes.itemById(PALETTE_ID)
        if palette:
            palette.deleteMe()
        for identity in (OPEN_ID, COMMIT_ID):
            definition = self.ui.commandDefinitions.itemById(identity)
            if definition:
                definition.deleteMe()
        self.handlers.clear()
        if self._log_handler:
            self.log.removeHandler(self._log_handler)
            self._log_handler.close()
