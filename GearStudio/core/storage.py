"""Bounded JSON preferences for Gear Studio, outside the add-in installation.

Settings preserve expression strings exactly. Only ``remember_success`` updates
last-used settings, and callers must invoke it after a successful geometry commit.
Defaults and presets are templates: document identity and placement are removed.
Reads return copies. Writes use same-directory atomic replacement. A future schema
is readable only as empty defaults and is never overwritten by this version.

``status`` and ``warnings`` expose recoverable load problems to the host UI.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
import uuid


SCHEMA_VERSION = 1
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_SPEC_BYTES = 32 * 1024
MAX_PRESETS = 100
MAX_FAMILIES = 64
MAX_PARAMETERS = 64
MAX_EXPRESSION_LENGTH = 512
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,79}\Z")


class StorageError(ValueError):
    """A settings operation could not complete safely."""


def _default_path() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        configured = os.environ.get("XDG_CONFIG_HOME")
        root = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / ".config"
    return root / "GearStudio" / "settings.json"


def _empty_state() -> dict:
    return {"schema_version": SCHEMA_VERSION, "last_used": {}, "last_kind": "spur", "presets": []}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_bytes(value) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise StorageError("Settings must contain ordinary JSON values and finite numbers.") from exc


def _template(spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise StorageError("A gear definition must be an object.")
    if len(_json_bytes(spec)) > MAX_SPEC_BYTES:
        raise StorageError("This gear definition is too large to save; keep it within 32 KB.")
    version = spec.get("schema_version", SCHEMA_VERSION)
    if type(version) is not int or version != SCHEMA_VERSION:
        raise StorageError("This gear definition uses an unsupported schema version.")
    kind = spec.get("kind")
    if not isinstance(kind, str) or not _IDENTIFIER.fullmatch(kind):
        raise StorageError("A gear definition needs a valid gear type.")
    name = spec.get("name", "Gear")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise StorageError("Use a gear name between 1 and 120 characters.")
    parameters = spec.get("parameters")
    if not isinstance(parameters, dict) or not parameters or len(parameters) > MAX_PARAMETERS:
        raise StorageError("A gear definition needs between 1 and 64 parameter expressions.")
    for key, expression in parameters.items():
        if not isinstance(key, str) or not _IDENTIFIER.fullmatch(key):
            raise StorageError("Parameter names must start with a letter and contain letters, digits or underscores.")
        if (not isinstance(expression, str) or not expression.strip()
                or len(expression) > MAX_EXPRESSION_LENGTH):
            raise StorageError(f"'{key}' must contain an expression between 1 and 512 characters.")
    result = copy.deepcopy(spec)
    result["schema_version"] = SCHEMA_VERSION
    result["name"] = name
    result.pop("id", None)
    result["placement"] = {}
    return result


def _validate_state(value) -> dict:
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int:
        raise StorageError("Settings do not contain a valid schema version.")
    if value["schema_version"] != SCHEMA_VERSION:
        raise StorageError("Settings use an unsupported schema version.")
    last_used, presets = value.get("last_used"), value.get("presets")
    if not isinstance(last_used, dict) or len(last_used) > MAX_FAMILIES:
        raise StorageError("Last-used settings are invalid or exceed the supported family count.")
    if not isinstance(presets, list) or len(presets) > MAX_PRESETS:
        raise StorageError("Saved presets are invalid or exceed the limit of 100 presets.")
    result = _empty_state()
    last_kind = value.get("last_kind", "spur")
    if not isinstance(last_kind, str) or not _IDENTIFIER.fullmatch(last_kind):
        raise StorageError("The last-used gear type is invalid.")
    result["last_kind"] = last_kind
    for kind, spec in last_used.items():
        clean = _template(spec)
        if kind != clean["kind"]:
            raise StorageError("Last-used settings contain a mismatched gear type.")
        result["last_used"][kind] = clean
    seen = set()
    for item in presets:
        if not isinstance(item, dict):
            raise StorageError("A saved preset is malformed.")
        preset_id = item.get("id")
        if not isinstance(preset_id, str) or len(preset_id) > 80 or not preset_id or preset_id in seen:
            raise StorageError("Saved preset identities are invalid or duplicated.")
        seen.add(preset_id)
        name = _preset_name(item.get("name"))
        updated_at = item.get("updated_at")
        if not isinstance(updated_at, str) or len(updated_at) > 64:
            raise StorageError("A saved preset has an invalid date.")
        result["presets"].append({"id": preset_id, "name": name,
                                  "spec": _template(item.get("spec")), "updated_at": updated_at})
    return result


def _preset_name(name) -> str:
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        raise StorageError("Use a preset name between 1 and 80 characters.")
    if any(ord(char) < 32 for char in name):
        raise StorageError("Preset names cannot contain line breaks or control characters.")
    return name.strip()


class SettingsStore:
    """Persistent defaults and named presets with atomic, recoverable writes.

    ``path`` is an optional JSON file path, useful for testing or enterprise
    configuration. Saving an existing preset name (case-insensitive) updates the
    same preset identity. A missing delete target raises ``StorageError``.
    """

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else _default_path()
        self.status = ""
        self.warnings = []
        self._lock = threading.RLock()
        self._blocked = False

    def _warn(self, message):
        self.status = message
        if message not in self.warnings:
            self.warnings.append(message)

    def _read(self) -> dict:
        self._blocked = False
        if not self.path.exists():
            return _empty_state()
        try:
            with self.path.open("rb") as handle:
                raw = handle.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise StorageError("Settings exceeded the 2 MB size limit.")
            def reject_constant(text):
                raise StorageError(f"Settings contain a nonfinite numeric value: {text}.")
            value = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
            if (isinstance(value, dict) and type(value.get("schema_version")) is int
                    and value["schema_version"] > SCHEMA_VERSION):
                self._blocked = True
                self._warn("These settings were written by a newer Gear Studio version. Defaults are available, but saving is disabled to protect that file.")
                return _empty_state()
            return _validate_state(value)
        except OSError as exc:
            self._blocked = True
            self._warn(f"Gear Studio could not read its settings. Check access to {self.path.parent}: {exc}")
            return _empty_state()
        except (StorageError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            backup = self.path.with_name(self.path.name + ".corrupt." + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "." + uuid.uuid4().hex[:8])
            try:
                os.replace(self.path, backup)
                self._warn(f"Gear Studio recovered from invalid settings ({exc}). The original file was preserved as {backup.name}.")
            except OSError as backup_error:
                self._blocked = True
                self._warn(f"Gear Studio could not back up invalid settings. Saving is disabled to protect the original file: {backup_error}")
            return _empty_state()

    def load(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._read())

    def last_spec(self, kind) -> dict | None:
        with self._lock:
            return copy.deepcopy(self._read()["last_used"].get(kind))

    def _write(self, state: dict):
        if self._blocked:
            raise StorageError(self.status or "Settings are read-only.")
        state = _validate_state(state)
        data = _json_bytes(state)
        if len(data) > MAX_FILE_BYTES:
            raise StorageError("Settings would exceed 2 MB. Remove unused presets before saving more.")
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="wb", prefix=".gearstudio-", suffix=".tmp",
                                             dir=self.path.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            temporary = None
        except OSError as exc:
            raise StorageError(f"Gear Studio could not save settings. Check write access and free disk space in {self.path.parent}: {exc}") from exc
        finally:
            if temporary is not None:
                try:
                    temporary.unlink()
                except OSError:
                    pass

    def remember_success(self, spec):
        template = _template(spec)
        with self._lock:
            state = self._read()
            state["last_used"][template["kind"]] = template
            state["last_kind"] = template["kind"]
            self._write(state)

    def list_presets(self) -> list:
        with self._lock:
            return copy.deepcopy(self._read()["presets"])

    def save_preset(self, name, spec) -> dict:
        name, template = _preset_name(name), _template(spec)
        with self._lock:
            state = self._read()
            existing = next((item for item in state["presets"] if item["name"].casefold() == name.casefold()), None)
            if existing is None and len(state["presets"]) >= MAX_PRESETS:
                raise StorageError("You have reached 100 presets. Remove one or reuse an existing name.")
            item = {"id": existing["id"] if existing else str(uuid.uuid4()),
                    "name": name, "spec": template, "updated_at": _timestamp()}
            if existing:
                state["presets"][state["presets"].index(existing)] = item
            else:
                state["presets"].append(item)
            self._write(state)
            return copy.deepcopy(item)

    def delete_preset(self, preset_id):
        with self._lock:
            state = self._read()
            remaining = [item for item in state["presets"] if item["id"] != preset_id]
            if len(remaining) == len(state["presets"]):
                raise StorageError("That preset no longer exists. Refresh the preset list.")
            state["presets"] = remaining
            self._write(state)
