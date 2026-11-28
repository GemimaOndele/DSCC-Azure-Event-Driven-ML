import json
from pathlib import Path

import joblib
import numpy as np
import onnx
import onnxruntime
import pandas as pd
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType, StringTensorType
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from prepare_data import ensure_dataset


RANDOM_SEED = 42
MODEL_VERSION = "1.1.0"
# The case workbook still contains these columns, but their availability before
# Churn is not documented. The 27/11/2026 decision excludes them from the model.
EXCLUDED_FROM_MODEL = ("numAdminTickets", "numTechTickets")
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "model"
MODEL_PATH = OUTPUT_DIR / f"model-{MODEL_VERSION}.joblib"
ONNX_MODEL_PATH = OUTPUT_DIR / f"model-{MODEL_VERSION}.onnx"
METRICS_PATH = OUTPUT_DIR / "metrics.json"
FEATURES_PATH = OUTPUT_DIR / "features.json"
TEST_SPLIT_PATH = OUTPUT_DIR / "test_split.csv"
IDENTIFIER = "customerID"
TARGET = "Churn"


def main() -> None:
    dataset_path = ensure_dataset()
    features_contract = json.loads(FEATURES_PATH.read_text(encoding="utf-8"))
    expected_features = [feature["name"] for feature in features_contract["features"]]
    if features_contract["model_version"] != MODEL_VERSION:
        raise ValueError("The feature contract targets a different model version.")
    if features_contract["feature_count"] != len(expected_features):
        raise ValueError("The feature contract is internally inconsistent.")

    data = pd.read_csv(dataset_path)
    customer_ids = data[IDENTIFIER].copy()
    data = data.drop(columns=[IDENTIFIER])
    data["TotalCharges"] = pd.to_numeric(data["TotalCharges"], errors="coerce")

    X = data.drop(columns=[TARGET, *EXCLUDED_FROM_MODEL])
    y = data[TARGET].map({"No": 0, "Yes": 1})

    if y.isna().any():
        raise ValueError("The Churn column contains values outside 'Yes'/'No'.")
    if X.columns.tolist() != expected_features:
        raise ValueError(
            "Dataset features do not match model/features.json: "
            f"{X.columns.tolist()} != {expected_features}"
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_SEED,
        stratify=y,
    )

    # Held-out split kept as evidence for the report. customerID and Churn are
    # reattached for reading only; neither is used by the model.
    test_split = X_test.copy()
    test_split.insert(0, IDENTIFIER, customer_ids.loc[X_test.index].to_numpy())
    test_split[TARGET] = y_test.map({0: "No", 1: "Yes"}).to_numpy()

    numeric_columns = X.select_dtypes(include=["number"]).columns.tolist()
    categorical_columns = X.select_dtypes(exclude=["number"]).columns.tolist()
    initial_types = [
        (
            column,
            FloatTensorType([None, 1])
            if column in numeric_columns
            else StringTensorType([None, 1]),
        )
        for column in X.columns
    ]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_columns),
            ("categorical", categorical_pipeline, categorical_columns),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=RANDOM_SEED,
                ),
            ),
        ]
    )
    model.fit(X_train, y_train)

    predicted = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]
    onnx_model = convert_sklearn(
        model,
        initial_types=initial_types,
        options={id(model.named_steps["classifier"]): {"zipmap": False}},
    )
    onnx.checker.check_model(onnx_model)

    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(X_train, y_train)
    baseline_predicted = baseline.predict(X_test)
    baseline_probabilities = baseline.predict_proba(X_test)[:, 1]

    metrics = {
        "model_version": MODEL_VERSION,
        "random_seed": RANDOM_SEED,
        "test_size": len(X_test),
        "decision_threshold": features_contract["decision_threshold"],
        "features": expected_features,
        "model": {
            "auc": float(roc_auc_score(y_test, probabilities)),
            "f1": float(f1_score(y_test, predicted)),
            "accuracy": float(accuracy_score(y_test, predicted)),
            "confusion_matrix": confusion_matrix(y_test, predicted).tolist(),
        },
        "naive_baseline_most_frequent": {
            "auc": float(roc_auc_score(y_test, baseline_probabilities)),
            "f1": float(f1_score(y_test, baseline_predicted, zero_division=0)),
            "accuracy": float(accuracy_score(y_test, baseline_predicted)),
            "confusion_matrix": confusion_matrix(y_test, baseline_predicted).tolist(),
        },
        "dataset": {
            "rows": int(len(data)),
            "features": int(X.shape[1]),
            "positive_class": "Yes",
            "positive_rows": int(y.sum()),
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    test_split.to_csv(TEST_SPLIT_PATH, index=False)
    joblib.dump(model, MODEL_PATH)
    ONNX_MODEL_PATH.write_bytes(onnx_model.SerializeToString())

    session = onnxruntime.InferenceSession(
        str(ONNX_MODEL_PATH),
        providers=["CPUExecutionProvider"],
    )
    onnx_inputs = {}
    for column in X.columns:
        dtype = np.float32 if column in numeric_columns else object
        onnx_inputs[column] = X_test[[column]].to_numpy(dtype=dtype)

    onnx_outputs = session.run(None, onnx_inputs)
    probability_outputs = [
        output
        for output in onnx_outputs
        if getattr(output, "ndim", 0) == 2 and output.shape[1] == 2
    ]
    if len(probability_outputs) != 1:
        raise RuntimeError("Could not identify the ONNX class-probability output.")

    onnx_probabilities = probability_outputs[0][:, 1]
    if not np.allclose(probabilities, onnx_probabilities, rtol=1e-4, atol=1e-5):
        raise RuntimeError("ONNX probabilities do not match the trained model.")

    metrics["onnx_max_probability_error"] = float(
        np.max(np.abs(probabilities - onnx_probabilities))
    )
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(json.dumps(metrics, indent=2))
    print(f"Model saved to {MODEL_PATH}")
    print(f"ONNX model saved to {ONNX_MODEL_PATH}")


if __name__ == "__main__":
    main()
