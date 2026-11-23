"""Shared data loading, Test guard and Validation selection (AFN-019/020/021).

Inputs are always given as paths (manifest JSONL, split CSV, image root); no
machine path is hard-coded. Only ``status == "accepted"`` manifest rows are
used. The Test split is locked: loaders refuse to materialise it unless the
caller passes ``allow_test=True``, which only the post-freeze evaluation
(#50, after #49 sign-off) may do.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from ml import REPO_ROOT

DEFAULT_EXPERIMENT_CONFIG = REPO_ROOT / "configs" / "experiment.yaml"
MANIFEST_SCHEMA_VERSION = "afn-manifest-v1"
SPLITS = ("train", "validation", "test")
LABELS = ("fake", "real")
TRAIN_VAL = ("train", "validation")


class DataContractError(ValueError):
    """Manifest/split inputs violate the data contract."""


class TestSplitLockedError(PermissionError):
    """Test rows were requested before the model freeze (#49)."""

    __test__ = False  # not a pytest test class


class FitOnNonTrainError(ValueError):
    """A feature extractor or classifier was about to be fit on non-Train rows."""


class SampleOrderError(ValueError):
    """Two feature blocks do not describe the same samples in the same order."""


# --------------------------------------------------------------------- config


def load_experiment_config(path: Path | str | None = None) -> dict[str, Any]:
    import yaml

    cfg_path = Path(path) if path else DEFAULT_EXPERIMENT_CONFIG
    with cfg_path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    for key in ("seed", "selection", "logistic_regression", "text_features", "fusion"):
        if key not in cfg:
            raise DataContractError(f"experiment config missing '{key}'")
    if cfg.get("fit_split", "train") != "train":
        raise DataContractError("protocol requires fit_split: train")
    if cfg.get("refit_on_train_and_validation"):
        raise DataContractError("protocol forbids refit on Train+Validation")
    return cfg


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ----------------------------------------------------------------------- data


@dataclass(frozen=True)
class Sample:
    sample_id: str
    label: str
    split: str
    title: str | None
    body: str
    group_id: str | None
    image_path: Path | None
    image_sha256: str | None
    is_fixture: bool


@dataclass
class Dataset:
    """Accepted samples per split, each list sorted by ``sample_id``."""

    splits: dict[str, list[Sample]]
    manifest_sha256: str
    split_sha256: str
    locked_counts: dict[str, int] = field(default_factory=dict)

    def rows(self, split: str) -> list[Sample]:
        if split not in self.splits:
            raise TestSplitLockedError(f"split '{split}' was not loaded")
        return self.splits[split]

    @property
    def is_fixture(self) -> bool:
        return any(s.is_fixture for rows in self.splits.values() for s in rows)


def read_split_file(path: Path | str) -> dict[str, str]:
    """CSV with header ``sample_id,split`` (proposed interface for DATA #18)."""
    mapping: dict[str, str] = {}
    with Path(path).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or not {"sample_id", "split"} <= set(reader.fieldnames):
            raise DataContractError("split file needs columns sample_id,split")
        for row in reader:
            sid, split = row["sample_id"].strip(), row["split"].strip()
            if split not in SPLITS:
                raise DataContractError(f"unknown split '{split}' for {sid}")
            if sid in mapping:
                raise DataContractError(f"duplicate sample_id in split file: {sid}")
            mapping[sid] = split
    return mapping


def load_dataset(
    manifest_path: Path | str,
    split_path: Path | str,
    image_root: Path | str | None = None,
    *,
    splits: Sequence[str] = TRAIN_VAL,
    allow_test: bool = False,
) -> Dataset:
    """Load accepted manifest rows assigned to ``splits``.

    Validates: schema version, unique ids, every split id is an accepted
    manifest row, labels, no group spanning several splits. Test rows are only
    counted (never parsed into samples) unless ``allow_test`` is True.
    """
    if "test" in splits and not allow_test:
        raise TestSplitLockedError("Test is locked until the #49 freeze sign-off")
    unknown = set(splits) - set(SPLITS)
    if unknown:
        raise DataContractError(f"unknown splits: {sorted(unknown)}")

    assignment = read_split_file(split_path)
    root = Path(image_root) if image_root is not None else Path(manifest_path).parent
    accepted: dict[str, dict] = {}
    seen: set[str] = set()
    with Path(manifest_path).open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("schema_version") != MANIFEST_SCHEMA_VERSION:
                raise DataContractError(f"line {line_no}: unexpected schema_version")
            sid = row["sample_id"]
            if sid in seen:
                raise DataContractError(f"duplicate sample_id in manifest: {sid}")
            seen.add(sid)
            if row.get("status") == "accepted":
                accepted[sid] = row

    missing = sorted(set(assignment) - set(accepted))
    if missing:
        raise DataContractError(f"split references non-accepted/missing ids: {missing[:5]}")

    group_split: dict[str, str] = {}
    for sid, split in assignment.items():
        gid = accepted[sid].get("group_id")
        if gid is None:
            continue
        if group_split.setdefault(gid, split) != split:
            raise DataContractError(f"group '{gid}' spans several splits")

    out: dict[str, list[Sample]] = {s: [] for s in splits}
    locked: dict[str, int] = {}
    for sid in sorted(assignment):
        split = assignment[sid]
        if split not in out:
            locked[split] = locked.get(split, 0) + 1
            continue
        row = accepted[sid]
        if row["label"] not in LABELS:
            raise DataContractError(f"bad label for {sid}")
        image = row.get("image") or {}
        out[split].append(Sample(
            sample_id=sid,
            label=row["label"],
            split=split,
            title=row.get("title"),
            body=row["body"],
            group_id=row.get("group_id"),
            image_path=(root / image["path"]) if image.get("path") else None,
            image_sha256=image.get("sha256"),
            is_fixture=bool(row.get("is_fixture")),
        ))
    return Dataset(out, sha256_file(manifest_path), sha256_file(split_path), locked)


def labels_to_y(samples: Iterable[Sample], positive: str = "fake") -> np.ndarray:
    return np.array([1 if s.label == positive else 0 for s in samples], dtype=np.int64)


def ids_of(samples: Iterable[Sample]) -> list[str]:
    return [s.sample_id for s in samples]


def require_train(samples: Sequence[Sample], what: str) -> None:
    """fit-Train guard: refuse to fit anything on Validation/Test rows."""
    bad = sorted({s.split for s in samples} - {"train"})
    if bad or not samples:
        raise FitOnNonTrainError(f"{what} may only be fit on Train rows (got {bad or 'none'})")


def order_digest(sample_ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sample_ids).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ selection


def make_logistic_regression(c: float, cfg: dict[str, Any]):
    from sklearn.linear_model import LogisticRegression

    lr = cfg["logistic_regression"]
    # scikit-learn >= 1.8 deprecates `penalty`; the protocol's "l2" is l1_ratio=0.
    if lr["penalty"] != "l2":
        raise DataContractError("only penalty: l2 is supported by the protocol")
    return LogisticRegression(
        C=c,
        solver=lr["solver"],
        l1_ratio=0.0,
        class_weight=lr["class_weight"],
        max_iter=lr["max_iter"],
        random_state=lr["random_state"],
    )


def fake_scores(model, X) -> np.ndarray:
    """Probability of the positive (fake=1) class, looked up via classes_."""
    idx = int(np.flatnonzero(model.classes_ == 1)[0])
    return model.predict_proba(X)[:, idx]


def macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    from sklearn.metrics import f1_score

    return float(f1_score(y_true, y_pred, labels=[1, 0], average="macro", zero_division=0))


def selection_key(score: float, c: float, threshold: float, decimals: int) -> tuple:
    """Higher score; ties -> threshold closest to 0.5, lower C, lower threshold."""
    return (-round(score, decimals), round(abs(threshold - 0.5), decimals), c, threshold)


@dataclass
class TuneResult:
    best_c: float
    best_threshold: float
    best_score: float
    grid: list[dict[str, float]]
    convergence_warnings: list[float]
    model: Any  # fitted on Train with best_c


def tune_on_validation(X_train, y_train, X_val, y_val, cfg: dict[str, Any]) -> TuneResult:
    """Fit on Train for each C, score thresholds on Validation, pick per protocol."""
    from sklearn.exceptions import ConvergenceWarning

    if len(set(y_train.tolist())) < 2:
        raise DataContractError("Train must contain both labels")
    sel = cfg["selection"]
    decimals = int(sel["metric_decimal_places"])
    if sel.get("threshold_comparison") != "greater_than_or_equal":
        raise DataContractError("only greater_than_or_equal thresholds are supported")
    grid: list[dict[str, float]] = []
    models: dict[float, Any] = {}
    not_converged: list[float] = []
    for c in sel["c_candidates"]:
        model = make_logistic_regression(float(c), cfg)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            model.fit(X_train, y_train)
        if any(issubclass(w.category, ConvergenceWarning) for w in caught):
            not_converged.append(float(c))
        models[float(c)] = model
        scores = fake_scores(model, X_val)
        for t in sel["threshold_candidates"]:
            pred = (scores >= float(t)).astype(np.int64)
            grid.append({"C": float(c), "threshold": float(t), "macro_f1": macro_f1(y_val, pred)})
    best = min(grid, key=lambda g: selection_key(g["macro_f1"], g["C"], g["threshold"], decimals))
    return TuneResult(best["C"], best["threshold"], best["macro_f1"], grid, not_converged,
                      models[best["C"]])


def runtime_versions() -> dict[str, str]:
    import scipy
    import sklearn

    from app.preprocessing import PREPROCESS_VERSION

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "preprocess_version": PREPROCESS_VERSION,
    }


def summarize_result(name: str, tune: TuneResult, *, feature_dim: int, train_ids: list[str],
                     val_ids: list[str], is_fixture: bool) -> dict[str, Any]:
    return {
        "configuration": name,
        "evidence_kind": "FIXTURE_SMOKE_NOT_RESEARCH" if is_fixture else "VALIDATION_ONLY",
        "feature_dim": int(feature_dim),
        "n_train": len(train_ids),
        "n_validation": len(val_ids),
        "train_order_sha256": order_digest(train_ids),
        "validation_order_sha256": order_digest(val_ids),
        "selected": {"C": tune.best_c, "threshold": tune.best_threshold,
                     "validation_macro_f1": tune.best_score},
        "grid": tune.grid,
        "convergence_warnings_for_C": tune.convergence_warnings,
    }
