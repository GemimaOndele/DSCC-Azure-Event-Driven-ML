import json
import shutil
import subprocess
import sys
from pathlib import Path

import onnx
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "model"
FEATURES_PATH = MODEL_DIR / "features.json"
METRICS_PATH = MODEL_DIR / "metrics.json"
ONNX_PATH = MODEL_DIR / "model-1.0.0.onnx"
# Shared blob of PR #17 and PR #18; a difference would mean a real artifact divergence.
EXPECTED_ONNX_GIT_SHA = "2fc9e022b7029f293bdc3a471f68a91f4d7e57ec"

sys.path.insert(0, str(MODEL_DIR))
from prepare_data import (  # noqa: E402
    EXPECTED_COLUMNS,
    PREPARED_PATH,
    SOURCE_SHA256,
    ensure_dataset,
)


def _run_isolated(target: Path) -> None:
    """Run the pinned pipeline in an isolated copy with the prepared CSV."""
    (target / "model").mkdir(parents=True, exist_ok=True)
    (target / "data" / "processed").mkdir(parents=True, exist_ok=True)
    shutil.copy2(PREPARED_PATH, target / "data" / "processed" / "churn_dataset.csv")
    for name in ("train.py", "prepare_data.py", "features.json"):
        shutil.copy2(MODEL_DIR / name, target / "model" / name)

    result = subprocess.run(
        [sys.executable, str(target / "model" / "train.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.fixture(scope="module")
def retrained(tmp_path_factory: pytest.TempPathFactory) -> Path:
    ensure_dataset()
    target = tmp_path_factory.mktemp("retrained")
    _run_isolated(target)
    return target


def test_dataset_matches_the_21_feature_contract() -> None:
    ensure_dataset()
    contract = json.loads(FEATURES_PATH.read_text(encoding="utf-8"))
    names = [feature["name"] for feature in contract["features"]]
    data = pd.read_csv(PREPARED_PATH)

    assert data.columns.tolist() == EXPECTED_COLUMNS
    assert data.shape == (7043, 23)
    assert len(names) == contract["feature_count"] == 21
    assert names == [column for column in data.columns if column not in {"customerID", "Churn"}]
    assert {"numAdminTickets", "numTechTickets"}.issubset(names)
    assert contract["identifier"] == "customerID"
    assert contract["target"] == "Churn"
    assert int(data["Churn"].eq("Yes").sum()) == 1869
    assert int(data["TotalCharges"].astype(str).str.strip().eq("").sum()) == 11
    # The source workbook is pinned; no silent data substitution is possible.
    assert SOURCE_SHA256 == "0f71b4ffadf837b37ad6a8747a2abdbb1b5e9db49d6e5847709ec8af01218760"


def test_committed_metrics_are_the_reference() -> None:
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))

    assert metrics["model_version"] == "1.0.0"
    assert metrics["random_seed"] == 42
    assert metrics["test_size"] == 1409
    assert metrics["decision_threshold"] == 0.5
    assert metrics["dataset"] == {
        "rows": 7043,
        "features": 21,
        "positive_class": "Yes",
        "positive_rows": 1869,
    }
    assert metrics["model"]["auc"] == pytest.approx(0.9272804774083547, abs=1e-12)
    assert metrics["model"]["f1"] == pytest.approx(0.7328072153325818, abs=1e-12)
    assert metrics["model"]["accuracy"] == pytest.approx(0.8317955997161107, abs=1e-12)
    assert metrics["model"]["confusion_matrix"] == [[847, 188], [49, 325]]
    assert metrics["naive_baseline_most_frequent"]["auc"] == 0.5
    assert metrics["model"]["auc"] > metrics["naive_baseline_most_frequent"]["auc"]
    assert metrics["onnx_max_probability_error"] < 1e-5
    assert len(metrics["features"]) == 21


def test_onnx_artifact_is_the_shared_version() -> None:
    blob_sha = subprocess.check_output(
        ["git", "hash-object", str(ONNX_PATH)], cwd=ROOT, text=True
    ).strip()
    assert blob_sha == EXPECTED_ONNX_GIT_SHA

    graph = onnx.load(str(ONNX_PATH)).graph
    onnx.checker.check_model(str(ONNX_PATH))
    assert len(graph.input) == 21
    assert [output.name for output in graph.output] == ["label", "probabilities"]
    probabilities = graph.output[1].type.tensor_type.shape
    assert probabilities.dim[-1].dim_value == 2


def test_test_split_is_the_held_out_evidence(retrained: Path) -> None:
    split = pd.read_csv(retrained / "model" / "test_split.csv")
    assert len(split) == 1409
    assert split.columns[0] == "customerID"
    assert split.columns[-1] == "Churn"
    assert set(split["Churn"]) == {"No", "Yes"}
    assert int(split["Churn"].eq("Yes").sum()) == 374
    assert "customerID" not in split.columns[1:-1]
    assert "Churn" not in split.columns[1:-1]


def test_training_reproduces_committed_metrics(retrained: Path, tmp_path: Path) -> None:
    """Rerun the pinned pipeline twice and compare every artefact."""
    ensure_dataset()
    second = tmp_path / "second"
    _run_isolated(second)

    committed = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    first_metrics = json.loads((retrained / "model" / "metrics.json").read_text(encoding="utf-8"))
    second_metrics = json.loads((second / "model" / "metrics.json").read_text(encoding="utf-8"))

    # ONNXRuntime reports this error at machine precision: its last digit can
    # differ between Windows and Linux. Every other value is exact.
    committed_error = committed.pop("onnx_max_probability_error")
    first_error = first_metrics.pop("onnx_max_probability_error")
    second_error = second_metrics.pop("onnx_max_probability_error")
    assert abs(committed_error - first_error) < 1e-5
    assert abs(first_error - second_error) < 1e-5
    assert first_metrics == second_metrics == committed
    assert (
        (retrained / "model" / "test_split.csv").read_bytes()
        == (second / "model" / "test_split.csv").read_bytes()
    )
