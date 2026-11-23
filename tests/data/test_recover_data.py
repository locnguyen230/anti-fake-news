import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import recover_data as recovery


class RecoveryResumeTest(unittest.TestCase):
    def test_resume_skips_saved_articles_and_audits_all_input_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = root / "dataset"
            dataset.mkdir()
            header = "id,news_url,title\n"
            for name in recovery.REQUIRED_CSV:
                (dataset / name).write_text(header, encoding="utf-8")
            inputs = dataset / "gossipcop_fake.csv"
            inputs.write_text(header + (
                "one,https://example.test/one,First fixture\n"
                "two,example.test/two,Second fixture\n"
                "missing,,Missing URL\n"
                "failed,https://example.test/failed,No article\n"
            ), encoding="utf-8")

            code = root / "code"
            credentials = code / "resources" / "tweet_keys_file.json"
            credentials.parent.mkdir(parents=True)
            credentials.write_text("{}", encoding="utf-8")
            (code / "main.py").touch()
            original_config = code / "config.json"
            original_config.write_text("original config", encoding="utf-8")
            attempted_ids = []

            def fake_collector(pending_dir):
                config = json.loads((pending_dir / "config.json").read_text(encoding="utf-8"))
                self.assertEqual(config["dataset_dir"], str(pending_dir))
                with (pending_dir / inputs.name).open(encoding="utf-8", newline="") as file:
                    rows = list(csv.DictReader(file))
                ids = [row["id"] for row in rows]
                attempted_ids.append(ids)
                source_id = ids[0]
                output = Path(config["dump_location"]) / "gossipcop" / "fake" / source_id
                output.mkdir(parents=True)
                (output / "news content.json").write_text(
                    json.dumps({"title": "Fixture", "text": "Synthetic body."}), encoding="utf-8"
                )
                if len(attempted_ids) == 1:
                    raise KeyboardInterrupt()

            journal = root / "validation_reports" / "recovery-attempts.jsonl"
            args = ["recover_data.py", "--repo", str(root)]
            with (
                patch.object(sys, "argv", args),
                patch.object(recovery, "run_fakenewsnet", side_effect=fake_collector),
                patch.object(recovery.requests, "get", side_effect=AssertionError("No network expected")),
            ):
                with self.assertRaises(KeyboardInterrupt):
                    recovery.main()
                interrupted = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
                self.assertEqual(sum(row["status"] == "pending" for row in interrupted), 3)
                recovery.main()

            self.assertEqual(attempted_ids, [["one", "two", "failed"], ["two", "failed"]])
            self.assertEqual(original_config.read_text(encoding="utf-8"), "original config")
            rows = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 4)
            self.assertEqual(len({row["sample_id"] for row in rows}), 4)
            self.assertEqual([row["status"] for row in rows], ["recovered", "recovered", "excluded", "excluded"])
            self.assertEqual(rows[2]["exclusion_reason"], "missing_url")
            self.assertEqual(rows[3]["exclusion_reason"], "article_not_recovered")
            self.assertTrue(rows[0]["article_saved_at"].endswith("+00:00"))
            self.assertTrue(rows[3]["recorded_at"].endswith("+00:00"))

    def test_duplicate_ids_are_rejected_before_collection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset = root / "dataset"
            dataset.mkdir()
            header = "id,news_url,title\n"
            for name in recovery.REQUIRED_CSV:
                (dataset / name).write_text(header, encoding="utf-8")
            (dataset / "gossipcop_fake.csv").write_text(
                header + "one,https://example.test/one,A\none,https://example.test/one,B\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                recovery.prepare_pending_inputs(dataset, root / "pending", root / "raw")


if __name__ == "__main__":
    unittest.main()
