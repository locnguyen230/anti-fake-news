"""#34 deliverables: selection reasons, Validation metrics, validation-search.json, selected-models.json."""

import json

import numpy as np

from ml.common import selection_reason, validation_metrics
from ml.run_experiments import main as run_experiments_main


def _g(c, t, f1):
    return {"C": c, "threshold": t, "macro_f1": f1}


def test_unique_best_is_decided_by_score():
    reason = selection_reason([_g(1.0, 0.5, 0.8), _g(0.1, 0.5, 0.7), _g(1.0, 0.3, 0.6)], 12)
    assert reason["decided_by"] == "highest_macro_f1"
    assert reason["tied_at_best"] == [{"C": 1.0, "threshold": 0.5}]
    assert reason["next_best_macro_f1"] == 0.7
    assert reason["margin_to_next_best"] == 0.1


def test_each_tie_break_step_is_reported():
    by_threshold = selection_reason([_g(1.0, 0.3, 0.8), _g(1.0, 0.6, 0.8)], 12)
    assert by_threshold["decided_by"] == "closest_threshold_to_0_5"
    by_c = selection_reason([_g(10.0, 0.5, 0.8), _g(0.1, 0.5, 0.8)], 12)
    assert by_c["decided_by"] == "lower_c"
    assert by_c["tied_at_best"][0] == {"C": 0.1, "threshold": 0.5}
    by_low_t = selection_reason([_g(1.0, 0.6, 0.8), _g(1.0, 0.4, 0.8)], 12)
    assert by_low_t["decided_by"] == "lower_threshold"
    assert by_low_t["tied_at_best"][0]["threshold"] == 0.4
    assert by_low_t["next_best_macro_f1"] is None


def test_ties_use_rounded_scores():
    reason = selection_reason([_g(1.0, 0.5, 0.8 + 1e-15), _g(0.1, 0.5, 0.8)], 12)
    assert reason["decided_by"] == "lower_c"


def test_validation_metrics_confusion_matrix_orientation():
    y_true = np.array([1, 1, 1, 0, 0])
    y_pred = np.array([1, 0, 1, 0, 1])
    m = validation_metrics(y_true, y_pred)
    assert m["confusion_matrix"]["rows_true_cols_pred"] == [[2, 1], [1, 1]]
    assert m["per_class"]["fake"]["support"] == 3 and m["per_class"]["real"]["support"] == 2
    assert m["accuracy"] == 0.6


def test_runner_writes_search_report_and_selected_models(ml_fixture, tmp_path):
    search, selected = tmp_path / "reports" / "validation-search.json", tmp_path / "configs" / "selected.json"
    assert run_experiments_main([
        "--manifest", str(ml_fixture["manifest"]), "--split", str(ml_fixture["split"]),
        "--configs", "text-only", "--out-dir", str(tmp_path / "runs"),
        "--search-report", str(search), "--selected-models", str(selected),
    ]) == 0
    report = json.loads(search.read_text())
    text = report["results"]["text-only"]
    assert report["test_split"]["loaded"] is False
    assert len(text["grid"]) == 25
    assert set(text["fit_seconds_by_C"]) == {"0.01", "0.1", "1.0", "10.0", "100.0"}
    assert text["timing_seconds"]["tune"] >= 0 and "text" in text["timing_seconds"]["shared_features"]
    assert text["selection_reason"]["candidates_evaluated"] == 25
    assert "confusion_matrix" in text["validation_metrics"]

    chosen = json.loads(selected.read_text())
    assert chosen["status"] == "candidate" and chosen["evidence_kind"] == "FIXTURE_SMOKE_NOT_RESEARCH"
    assert chosen["inputs"] == report["inputs"]
    assert chosen["configurations"]["text-only"]["C"] == text["selected"]["C"]
    assert chosen["configurations"]["text-only"]["threshold"] == text["selected"]["threshold"]
