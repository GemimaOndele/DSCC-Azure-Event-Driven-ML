"""Reproducible preparation of the DSCC churn dataset (no redistribution).

The case workbook is **not** committed to this public repository. It is fetched
from its public source with a pinned SHA-256, then converted to a local CSV that
is ignored by Git. This answers the integration review on PR #18: the source
data and the test split are no longer redistributed, and the preparation is
reproducible from a documented source.

The two ticket counters are supplied by the case workbook itself (they are not
present in the upstream IBM CSV). They are *not* generated here, and this module
never reads the ``Churn`` column to build a feature.
"""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Public DSCC/PwC-Forage case repository. The workbook is retrieved, not hosted
# here; reuse beyond the DSCC educational context requires the case owner's
# permission. See model/DATASET.md for the full provenance discussion.
SOURCE_URL = (
    "https://raw.githubusercontent.com/TimKong21/"
    "telecom-customer-operations-decision-hub/main/"
    "reports/Task%202%20-%20Customer%20Retention/02%20Churn-Dataset.xlsx"
)
SOURCE_SHA256 = "0f71b4ffadf837b37ad6a8747a2abdbb1b5e9db49d6e5847709ec8af01218760"
SHEET = "01 Churn-Dataset"
EXPECTED_COLUMNS = [
    "customerID",
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "numAdminTickets",
    "numTechTickets",
    "Churn",
]

RAW_PATH = ROOT / "data" / "raw" / "02-Churn-Dataset.xlsx"
PREPARED_PATH = ROOT / "data" / "processed" / "churn_dataset.csv"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_source() -> Path:
    """Fetch the pinned case workbook and verify its checksum."""
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RAW_PATH.exists() and _sha256(RAW_PATH) == SOURCE_SHA256:
        return RAW_PATH

    with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
        with RAW_PATH.open("wb") as target:
            shutil.copyfileobj(response, target)

    actual = _sha256(RAW_PATH)
    if actual != SOURCE_SHA256:
        RAW_PATH.unlink(missing_ok=True)
        raise RuntimeError(
            "Case workbook checksum mismatch: "
            f"expected {SOURCE_SHA256}, got {actual}. "
            "Do not train on an unverified source."
        )
    return RAW_PATH


def ensure_dataset() -> Path:
    """Return the local CSV, creating it from the pinned workbook if needed."""
    if PREPARED_PATH.exists():
        return PREPARED_PATH

    workbook = download_source()
    frame = pd.read_excel(workbook, sheet_name=SHEET)
    if frame.columns.tolist() != EXPECTED_COLUMNS:
        raise ValueError(
            "Unexpected case-workbook columns: "
            f"{frame.columns.tolist()} != {EXPECTED_COLUMNS}"
        )
    if len(frame) != 7043:
        raise ValueError(f"Unexpected case-workbook row count: {len(frame)}")

    PREPARED_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(PREPARED_PATH, index=False)
    return PREPARED_PATH


if __name__ == "__main__":
    print(ensure_dataset())
