"""Kiểm tra độc lập định dạng và nguồn gốc fixture QA bằng unittest."""

import json
from pathlib import Path
import tempfile
import unittest

from generate_fixtures import generate, make_png


ROOT = Path(__file__).resolve().parent
VERSION = ROOT / "v0.1.1"


class FixtureRegistryTests(unittest.TestCase):
    def test_manifest_paths_are_present_and_owned(self):
        manifest = json.loads((VERSION / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["fixture_version"], "v0.1.1")
        self.assertEqual(manifest["owner"], "QA (dangnguyen0512)")
        ids = [entry["id"] for entry in manifest["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        for entry in manifest["entries"]:
            self.assertTrue(entry["source"].startswith("synthetic"))
            if "path" in entry:
                self.assertTrue((VERSION / entry["path"]).is_file(), entry["path"])

    def test_contract_examples_have_no_secrets(self):
        for filename in ("empty-text.json", "request-valid-fields.json", "session-race.json", "split-policy.json"):
            content = (VERSION / filename).read_text(encoding="utf-8")
            json.loads(content)
            for marker in ("BEGIN PRIVATE KEY", "ghp_", "sk-proj-", "AFN_DEMO_TOKEN="):
                self.assertNotIn(marker, content)

    def test_generated_cases_have_expected_boundaries(self):
        with tempfile.TemporaryDirectory(prefix="afn-qa-check-") as temp:
            names = generate(temp)
            self.assertEqual(len(names), 5)
            folder = Path(temp)
            self.assertEqual(len((folder / "long-text.txt").read_text()), 50001)
            self.assertEqual((folder / "corrupt.png").read_bytes(), b"not-an-image")
            self.assertTrue((folder / "valid.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual((folder / "wrong-mime.txt").read_bytes(), make_png())
            self.assertEqual((folder / "oversized.png").stat().st_size, 10 * 1024 * 1024 + 1)

    def test_race_and_split_synthetic_metadata(self):
        race = json.loads((VERSION / "session-race.json").read_text(encoding="utf-8"))
        self.assertEqual(race["response_order"], list(reversed(race["send_order"])))
        self.assertEqual(race["expected_visible_request"], "request_b")
        split = json.loads((VERSION / "split-policy.json").read_text(encoding="utf-8"))
        self.assertAlmostEqual(sum(split["split_proportions"].values()), 1)
        self.assertFalse(split["contains_research_data"])
        self.assertTrue(split["test_allowed_only_after_freeze"])


if __name__ == "__main__":
    unittest.main()
