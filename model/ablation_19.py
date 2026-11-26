"""Reproducible ablation: train the same model with and without the two ticket counters.

This is a decision aid for the open 19 vs 21 feature question (issues #2, #4,
#18). It never writes a model, a metric file or a split: the shared ONNX
artefact and model/metrics.json stay untouched. Run with:

    py -3.12 model/ablation_19.py
"""

import json
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from prepare_data import ensure_dataset


ROOT = Path(__file__).resolve().parents[1]
RANDOM_SEED = 42
TICKET_COLUMNS = ("numAdminTickets", "numTechTickets")


def _score(features: list[str]) -> dict[str, object]:
    data = pd.read_csv(ensure_dataset())
    X = data[features].copy()
    X["TotalCharges"] = pd.to_numeric(X["TotalCharges"], errors="coerce")
    y = data["Churn"].map({"No": 0, "Yes": 1})
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_SEED,
        stratify=y,
    )

    numeric_columns = X.select_dtypes(include=["number"]).columns.tolist()
    categorical_columns = X.select_dtypes(exclude=["number"]).columns.tolist()
    model = Pipeline(
        steps=[
            (
                "preprocessor",
                ColumnTransformer(
                    transformers=[
                        (
                            "numeric",
                            Pipeline(
                                steps=[
                                    ("imputer", SimpleImputer(strategy="median")),
                                    ("scaler", StandardScaler()),
                                ]
                            ),
                            numeric_columns,
                        ),
                        (
                            "categorical",
                            Pipeline(
                                steps=[
                                    ("encoder", OneHotEncoder(handle_unknown="ignore")),
                                ]
                            ),
                            categorical_columns,
                        ),
                    ]
                ),
            ),
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
    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = model.predict(X_test)
    baseline = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)

    return {
        "features": len(features),
        "test_rows": int(len(X_test)),
        "auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "f1": round(float(f1_score(y_test, predictions)), 4),
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "baseline_accuracy": round(
            float(accuracy_score(y_test, baseline.predict(X_test))), 4
        ),
    }


def main() -> None:
    contract = json.loads((ROOT / "model" / "features.json").read_text(encoding="utf-8"))
    expected = [feature["name"] for feature in contract["features"]]
    without_tickets = [
        name for name in expected if name not in TICKET_COLUMNS
    ]
    print(
        json.dumps(
            {
                "random_seed": RANDOM_SEED,
                "shared_model_version": contract["model_version"],
                "with_ticket_counters": _score(expected),
                "without_ticket_counters": _score(without_tickets),
                "note": "Read-only ablation; the committed ONNX artefact is unchanged.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
