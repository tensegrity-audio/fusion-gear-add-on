"""Reproduce Fusion's generated entry-point package without running __init__.py."""
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'GearStudio'


class FusionLoadingTests(unittest.TestCase):
    def test_generated_entrypoint_can_import_controller_and_run_without_package_init(self):
        name = '__main__C%3A%2FUsers%2Fgriff%2Ffusion-gear-add-on%2FGearStudio%2FGearStudio_py'
        specification = importlib.util.spec_from_file_location(
            name, PACKAGE / 'GearStudio.py', submodule_search_locations=[str(PACKAGE)])
        entry = importlib.util.module_from_spec(specification)
        adsk = ModuleType('adsk'); adsk.__path__ = []
        adsk.core = ModuleType('adsk.core'); adsk.fusion = ModuleType('adsk.fusion')
        for handler in ('CommandCreatedEventHandler', 'CommandEventHandler', 'HTMLEventHandler'):
            setattr(adsk.core, handler, object)
        with patch.dict(sys.modules, {name: entry, 'adsk': adsk, 'adsk.core': adsk.core,
                                      'adsk.fusion': adsk.fusion}):
            specification.loader.exec_module(entry)
            self.assertFalse(hasattr(entry, '__version__'), 'Fusion does not execute the package initializer.')
            controller = importlib.import_module(name + '.fusion.controller')
            manifest = json.loads((PACKAGE / 'GearStudio.manifest').read_text(encoding='utf-8'))
            self.assertEqual(controller.__version__, manifest['version'])
            native = Mock()
            with patch.object(controller, 'Controller', return_value=native):
                context = {'IsApplicationStartup': True}
                entry.run(context)
                native.start.assert_called_once_with(context)
                entry.stop({})
                native.stop.assert_called_once()
                self.assertIsNone(entry._controller)

    def test_package_manifest_and_development_versions_agree(self):
        from GearStudio import __version__
        manifest = json.loads((PACKAGE / 'GearStudio.manifest').read_text(encoding='utf-8'))
        package = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
        lock = json.loads((ROOT / 'package-lock.json').read_text(encoding='utf-8'))
        self.assertEqual({__version__, manifest['version'], package['version'],
                          lock['version'], lock['packages']['']['version']}, {__version__})


if __name__ == '__main__': unittest.main()
