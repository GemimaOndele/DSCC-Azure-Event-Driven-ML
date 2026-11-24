import json
import shutil
import subprocess
import sys
from pathlib import Path

import onnx
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "Customer_Churn_Dataset.xlsx"
MODEL_DIR = ROOT / "model"
FEATURES_PATH = MODEL_DIR / "features.json"
METRICS_PATH = MODEL_DIR / "metrics.json"
TEST_SPLIT_PATH = MODEL_DIR / "test_split.csv"
ONNX_PATH = MODEL_DIR / "model-1.0.0.onnx"
# Shared blob of PR #17 and PR #18; a difference would mean a real artifact divergence.
EXPECTED_ONNX_GIT_SHA = "2fc9e022b7029f293bdc3a471f68a91f4d7e57ec"


def test_dataset_matches_the_21_feature_contract() -> None:
    contract = json.loads(FEATURES_PATH.read_text(encoding="utf-8"))
    names = [feature["name"] for feature in contract["features"]]
    data = pd.read_excel(DATASET, sheet_name="01 Churn-Dataset")

    assert data.shape == (7043, 23)
    assert len(names) == contract["feature_count"] == 21
    assert names == [column for column in data.columns if column not in {"customerID", "Churn"}]
    assert {"numAdminTickets", "numTechTickets"}.issubset(names)
    assert contract["identifier"] == "customerID"
    assert contract["target"] == "Churn"
    assert int(data["Churn"].eq("Yes").sum()) == 1869
    assert int(data["TotalCharges"].astype(str).str.strip().eq("").sum()) == 11


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


def test_test_split_is_the_held_out_evidence() -> None:
    split = pd.read_csv(TEST_SPLIT_PATH)
    assert len(split) == 1409
    assert split.columns[0] == "customerID"
    assert split.columns[-1] == "Churn"
    assert set(split["Churn"]) == {"No", "Yes"}
    assert int(split["Churn"].eq("Yes").sum()) == 374
    assert "customerID" not in split.columns[1:-1]
    assert "Churn" not in split.columns[1:-1]


def test_training_reproduces_committed_metrics(tmp_path: Path) -> None:
    """Rerun the pinned pipeline in an isolated copy and compare artefacts."""
    isolated = tmp_path / "repo"
    (isolated / "model").mkdir(parents=True)
    shutil.copy2(DATASET, isolated / DATASET.name)
    for name in ("train.py", "features.json"):
        shutil.copy2(MODEL_DIR / name, isolated / "model" / name)

    result = subprocess.run(
        [sys.executable, str(isolated / "model" / "train.py")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (isolated / "model" / "metrics.json").read_bytes() == METRICS_PATH.read_bytes()
    assert (isolated / "model" / "test_split.csv").read_bytes() == TEST_SPLIT_PATH.read_bytes()
