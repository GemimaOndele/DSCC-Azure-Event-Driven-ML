"""Offline CPU latency benchmark for the committed ONNX model.

The benchmark uses synthetic rows built from model/features.json. It never
reads the case workbook, never downloads data and never publishes an artifact.
It measures only onnxruntime's CPUExecutionProvider, i.e. the model execution
time reported by the API as ``latency_ms`` (HTTP overhead excluded).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "model"
FEATURES_PATH = MODEL_DIR / "features.json"

# Representative in-contract values for numeric fields. They are used only to
# build valid ONNX inputs; the benchmark says nothing about model accuracy.
TYPICAL_NUMERIC = {
    "SeniorCitizen": 0,
    "tenure": 12,
    "MonthlyCharges": 70.0,
    "TotalCharges": 800.0,
}


def load_contract() -> dict[str, Any]:
    """Read the shared feature contract and check it is internally consistent."""
    contract = json.loads(FEATURES_PATH.read_text(encoding="utf-8"))
    names = [feature["name"] for feature in contract["features"]]
    if len(names) != contract["feature_count"] or len(set(names)) != len(names):
        raise ValueError("The feature contract is not internally consistent.")
    return contract


def synthetic_inputs(contract: dict[str, Any], rows: int) -> dict[str, np.ndarray]:
    """Build valid ONNX inputs from the contract only (no dataset access)."""
    if rows < 1:
        raise ValueError("rows must be a positive integer")
    inputs: dict[str, np.ndarray] = {}
    for index, feature in enumerate(contract["features"]):
        name = feature["name"]
        if feature["kind"] == "numeric":
            low, high = feature["allowed_range"]
            value = TYPICAL_NUMERIC.get(name, low + (high - low) / 2)
            if not low <= value <= high:
                raise ValueError(f"Typical value for {name} is outside its allowed range.")
            inputs[name] = np.full((rows, 1), value, dtype=np.float32)
        elif feature["kind"] == "categorical":
            values = feature["allowed_values"]
            inputs[name] = np.array(
                [[values[index % len(values)]] for index in range(rows)], dtype=object
            )
        else:
            raise ValueError(f"Unsupported feature kind: {feature['kind']}")
    return inputs


def git_blob_sha(path: Path) -> str:
    """Return the same SHA-1 that ``git hash-object`` reports for a file."""
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - git object identifier, not security


def _percentile(sorted_samples: list[float], quantile: float) -> float:
    index = max(0, math.ceil(quantile * len(sorted_samples)) - 1)
    return sorted_samples[index]


def measure(session: onnxruntime.InferenceSession, inputs: dict[str, np.ndarray], *,
            warmup: int, iterations: int) -> dict[str, float | int]:
    """Run warm-up calls, then time the ONNX inference only."""
    if warmup < 0 or iterations < 1:
        raise ValueError("warmup must be >= 0 and iterations must be >= 1")
    for _ in range(warmup):
        session.run(None, inputs)

    samples_ms: list[float] = []
    outputs: list[np.ndarray] = []
    for _ in range(iterations):
        started = time.perf_counter()
        outputs = session.run(None, inputs)
        samples_ms.append((time.perf_counter() - started) * 1000)

    probabilities = [
        output
        for output in outputs
        if getattr(output, "ndim", 0) == 2 and output.shape[1] == 2
    ]
    if len(probabilities) != 1:
        raise RuntimeError("Could not identify the ONNX class-probability output.")
    rows = next(iter(inputs.values())).shape[0]
    if probabilities[0].shape[0] != rows:
        raise RuntimeError("ONNX output does not contain one probability per row.")

    ordered = sorted(samples_ms)
    mean_ms = sum(samples_ms) / len(samples_ms)
    return {
        "rows": rows,
        "iterations": iterations,
        "warmup": warmup,
        "mean_ms": round(mean_ms, 6),
        "p50_ms": round(_percentile(ordered, 0.50), 6),
        "p95_ms": round(_percentile(ordered, 0.95), 6),
        "max_ms": round(ordered[-1], 6),
        "rows_per_second": round(rows / (mean_ms / 1000), 1) if mean_ms > 0 else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1, help="Rows per inference (default: 1)")
    parser.add_argument("--iterations", type=int, default=50, help="Timed calls (default: 50)")
    parser.add_argument("--warmup", type=int, default=5, help="Untimed calls (default: 5)")
    args = parser.parse_args()

    contract = load_contract()
    onnx_path = MODEL_DIR / f"model-{contract['model_version']}.onnx"
    session = onnxruntime.InferenceSession(
        str(onnx_path), providers=["CPUExecutionProvider"]
    )
    expected = [feature["name"] for feature in contract["features"]]
    actual = [model_input.name for model_input in session.get_inputs()]
    if actual != expected:
        raise RuntimeError(f"ONNX inputs do not match features.json: {actual} != {expected}")

    report = {
        "model_version": contract["model_version"],
        "onnx_git_blob_sha": git_blob_sha(onnx_path),
        "scope": "onnxruntime CPUExecutionProvider inference only; no HTTP, no dataset",
        "environment": {
            "python": platform.python_version(),
            "onnxruntime": onnxruntime.__version__,
            "platform": platform.platform(),
            "processor": platform.processor() or platform.machine(),
        },
        "latency": measure(
            session, synthetic_inputs(contract, args.rows),
            warmup=args.warmup, iterations=args.iterations,
        ),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
