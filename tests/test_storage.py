import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from GearStudio.core.storage import MAX_FILE_BYTES, SettingsStore, StorageError


def gear(kind="spur"):
    return {"schema_version": 1, "id": "document-gear-identity", "name": "Drive gear",
            "kind": kind, "parameters": {"teeth": "24 * 2", "module": "  sharedModule  ",
                                        "bore": "shaftDiameter + boreAllowance"},
            "placement": {"x": 12}}


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "config" / "settings.json"
        self.store = SettingsStore(self.path)

    def write_raw(self, text):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(text, encoding="utf-8")

    def test_missing_file_has_defaults_without_side_effects(self):
        self.assertIsNone(self.store.last_spec("spur"))
        self.assertEqual(self.store.list_presets(), [])
        self.assertFalse(self.path.exists())

    def test_success_persists_expressions_but_not_document_identity(self):
        spec = gear()
        original = copy.deepcopy(spec)
        self.store.remember_success(spec)
        restored = SettingsStore(self.path).last_spec("spur")
        self.assertEqual(restored["parameters"], spec["parameters"])
        self.assertNotIn("id", restored)
        self.assertEqual(restored["placement"], {})
        self.assertEqual(spec, original)
        restored["parameters"]["module"] = "9 mm"
        self.assertEqual(self.store.last_spec("spur")["parameters"]["module"], "  sharedModule  ")

    def test_gear_families_remember_independently(self):
        self.store.remember_success(gear())
        helical = gear("helical")
        helical["parameters"]["teeth"] = "12"
        self.store.remember_success(helical)
        self.assertEqual(self.store.last_spec("spur")["parameters"]["teeth"], "24 * 2")
        self.assertEqual(self.store.last_spec("helical")["parameters"]["teeth"], "12")

    def test_last_family_changes_only_after_a_successful_save(self):
        self.assertEqual(self.store.load()["last_kind"], "spur")
        self.store.remember_success(gear("helical"))
        self.store.save_preset("Ring", gear("internal_spur"))
        self.assertEqual(SettingsStore(self.path).load()["last_kind"], "helical")
        with mock.patch("GearStudio.core.storage.os.replace", side_effect=OSError("write failure")):
            with self.assertRaises(StorageError):
                self.store.remember_success(gear("worm"))
        self.assertEqual(self.store.load()["last_kind"], "helical")

    def test_older_settings_without_last_kind_are_compatible(self):
        self.write_raw(json.dumps({"schema_version": 1, "last_used": {}, "presets": []}))
        self.assertEqual(self.store.load()["last_kind"], "spur")
        self.assertEqual(list(self.path.parent.glob("*.corrupt.*")), [])
        self.store.remember_success(gear("rack"))
        self.assertEqual(self.store.load()["last_kind"], "rack")

    def test_invalid_saved_definition_does_not_replace_last_good(self):
        self.store.remember_success(gear())
        initial = self.path.read_bytes()
        invalid = gear()
        invalid["parameters"]["teeth"] = 0
        with self.assertRaises(StorageError):
            self.store.remember_success(invalid)
        self.assertEqual(self.path.read_bytes(), initial)

    def test_presets_update_by_name_without_changing_identity(self):
        first = self.store.save_preset("  Fine gears ", gear())
        modified = gear()
        modified["parameters"]["teeth"] = "12"
        second = self.store.save_preset("fine GEARS", modified)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.list_presets()), 1)
        self.assertNotIn("id", second["spec"])
        second["spec"]["parameters"]["teeth"] = "333"
        self.assertEqual(self.store.list_presets()[0]["spec"]["parameters"]["teeth"], "12")
        self.assertIsNone(self.store.last_spec("spur"))
        self.store.delete_preset(first["id"])
        self.assertEqual(self.store.list_presets(), [])
        with self.assertRaises(StorageError):
            self.store.delete_preset(first["id"])

    def test_malformed_file_is_backed_up_and_reported(self):
        corrupt = '{"schema_version":'
        self.write_raw(corrupt)
        self.assertEqual(self.store.load()["presets"], [])
        backups = list(self.path.parent.glob("settings.json.corrupt.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), corrupt)
        self.assertIn("preserved", self.store.status)
        self.store.remember_success(gear())
        self.assertIsNotNone(SettingsStore(self.path).last_spec("spur"))

    def test_future_schema_is_never_overwritten(self):
        original = json.dumps({"schema_version": 999, "important_future_data": "keep me"})
        self.write_raw(original)
        self.assertEqual(self.store.list_presets(), [])
        self.assertIn("newer", self.store.status)
        with self.assertRaises(StorageError):
            self.store.remember_success(gear())
        with self.assertRaises(StorageError):
            self.store.save_preset("Cannot save", gear())
        self.assertEqual(self.path.read_text(), original)
        self.assertEqual(list(self.path.parent.glob("*.corrupt.*")), [])

    def test_atomic_replace_failure_preserves_original(self):
        self.store.remember_success(gear())
        initial = self.path.read_bytes()
        with mock.patch("GearStudio.core.storage.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(StorageError, "could not save"):
                self.store.save_preset("New preset", gear())
        self.assertEqual(self.path.read_bytes(), initial)
        self.assertEqual(list(self.path.parent.glob(".gearstudio-*.tmp")), [])

    def test_corruption_backup_failure_blocks_write(self):
        self.write_raw("invalid")
        with mock.patch("GearStudio.core.storage.os.replace", side_effect=OSError("read only")):
            with self.assertRaises(StorageError):
                self.store.remember_success(gear())
        self.assertEqual(self.path.read_text(), "invalid")
        self.assertIn("Saving is disabled", self.store.status)

    def test_size_limits(self):
        oversized = gear()
        oversized["parameters"]["teeth"] = "1" * 513
        with self.assertRaises(StorageError):
            self.store.save_preset("Oversized", oversized)
        self.write_raw(" " * (MAX_FILE_BYTES + 1))
        self.assertEqual(self.store.load()["presets"], [])
        self.assertIn("size limit", self.store.status)

    def test_nonfinite_numbers_and_wrong_schema_are_not_accepted(self):
        for extra in [float("nan"), float("inf")]:
            spec = gear()
            spec["extra"] = extra
            with self.assertRaises(StorageError):
                self.store.remember_success(spec)
        spec = gear()
        spec["schema_version"] = True
        with self.assertRaises(StorageError):
            self.store.remember_success(spec)

    def test_preset_limit_allows_existing_preset_update(self):
        with mock.patch("GearStudio.core.storage.MAX_PRESETS", 2):
            self.store.save_preset("One", gear())
            self.store.save_preset("Two", gear())
            with self.assertRaises(StorageError):
                self.store.save_preset("Three", gear())
            updated = self.store.save_preset("One", gear("helical"))
            self.assertEqual(updated["spec"]["kind"], "helical")

    def test_load_returns_independent_state(self):
        self.store.remember_success(gear())
        state = self.store.load()
        state["last_used"].clear()
        self.assertIsNotNone(self.store.last_spec("spur"))


if __name__ == "__main__":
    unittest.main()
