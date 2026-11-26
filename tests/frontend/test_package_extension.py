import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import package_extension


class PackageExtensionTest(unittest.TestCase):
    def test_build_uses_only_the_runtime_allowlist_and_repeats_without_overwriting_extras(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "package"
            shutil.copytree(package_extension.SOURCE, source)
            (source / "modules" / "local-fixture.js").write_text("// local fixture", encoding="utf-8")
            (source / "local-fixture.json").write_text("{}", encoding="utf-8")

            with patch.object(package_extension, "SOURCE", source):
                config = package_extension.runtime_config('test-"token"')
                first_count = package_extension.build_extension(output, config)
                self.assertEqual(first_count, package_extension.build_extension(output, config))
                self.assertFalse((output / "modules" / "local-fixture.js").exists())
                self.assertFalse((output / "local-fixture.json").exists())
                manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
                self.assertTrue((output / manifest["action"]["default_popup"]).is_file())
                self.assertTrue((output / "popup.js").is_file())
                self.assertTrue((output / "styles" / "popup.css").is_file())
                self.assertTrue((output / "modules" / "result-view.js").is_file())
                self.assertFalse((output / "analyze.html").exists())
                self.assertEqual(json.loads((output / package_extension.RUNTIME_CONFIG).read_bytes()), {
                    "endpoint": "http://127.0.0.1:8000",
                    "demoToken": 'test-"token"',
                })
                with self.assertRaises(FileExistsError):
                    package_extension.build_extension(output, package_extension.runtime_config("rotated"))
                local = output / "local-note.txt"
                local.write_text("Local output", encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    package_extension.build_extension(output, config)
                self.assertEqual(local.read_text(encoding="utf-8"), "Local output")

    def test_reads_dotenv_with_process_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text('AFN_DEMO_TOKEN="dotenv-test"\nAFN_PORT=8765\n', encoding="utf-8")
            with patch.object(package_extension, "ROOT", root), patch.dict("os.environ", {}, clear=True):
                self.assertEqual(json.loads(package_extension.config_from_environment()), {
                    "endpoint": "http://127.0.0.1:8765",
                    "demoToken": "dotenv-test",
                })
                with patch.dict("os.environ", {"AFN_DEMO_TOKEN": "environment-test", "AFN_PORT": "9000"}):
                    self.assertEqual(json.loads(package_extension.config_from_environment()), {
                        "endpoint": "http://127.0.0.1:9000",
                        "demoToken": "environment-test",
                    })
                with patch.dict("os.environ", {"AFN_DEMO_TOKEN": ""}):
                    with self.assertRaisesRegex(ValueError, "AFN_DEMO_TOKEN"):
                        package_extension.config_from_environment()


if __name__ == "__main__":
    unittest.main()
