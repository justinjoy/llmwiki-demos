import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

class EngineVersionTests(unittest.TestCase):
    def engines(self):
        for i, path in enumerate(('shared/query.py', 'llmwiki-wirelog/llmwiki/engine.py')):
            spec = importlib.util.spec_from_file_location(f'engine_version_test_{i}', ROOT / path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            yield module

    def test_minimum_and_later_versions_are_accepted_and_reported(self):
        for engine in self.engines():
            for installed in ('1.1.2', '1.1.3', '1.10.0', '2.0.0'):
                with self.subTest(engine=engine.__name__, installed=installed), patch.object(engine, 'version', return_value=installed):
                    result = engine.evaluate('.decl edge(x: symbol)\n.decl result(x: symbol)\nresult(X) :- edge(X).', 'edge("ok").')
                    self.assertEqual(result['engine_version'], installed)
                    self.assertEqual(result['relations']['result'], [['ok']])

    def test_old_versions_and_minimum_prerelease_are_rejected(self):
        for engine in self.engines():
            for installed in ('0.1.0', '1.1.1', '1.1.2rc1'):
                with self.subTest(engine=engine.__name__, installed=installed), patch.object(engine, 'version', return_value=installed):
                    with self.assertRaisesRegex(RuntimeError, '1.1.2 이상'):
                        engine.require_pyrewire()

    def test_missing_package_explains_minimum_install_requirement(self):
        for engine in self.engines():
            with patch.object(engine, 'version', side_effect=engine.PackageNotFoundError):
                with self.assertRaisesRegex(RuntimeError, 'pyrewire>=1.1.2'):
                    engine.require_pyrewire()

if __name__ == '__main__':
    unittest.main()
