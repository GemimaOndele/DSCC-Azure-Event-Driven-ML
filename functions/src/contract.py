"""CSV contract validation, driven by the shared 21-feature JSON schema."""

from __future__ import annotations

import csv
import io
import json
import math
import re
from pathlib import Path
from typing import Any

from .config import Settings

FEATURES_PATH = Path(__file__).resolve().parents[1] / "contract" / "features.json"
MAX_REJECTED_ERRORS = 10
BLOB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
# Keep in sync with CustomerFeatures.customerID in the API (#17).
CUSTOMER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class CsvContractError(ValueError):
    """A file cannot be accepted: ``reason`` is written to ``rejected/``."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def load_feature_contract() -> dict[str, Any]:
    contract = json.loads(FEATURES_PATH.read_text(encoding="utf-8-sig"))
    if contract["feature_count"] != 21 or len(contract["features"]) != 21:  # pragma: no cover
        raise ValueError("Inconsistent feature contract")
    return contract


def required_columns() -> list[str]:
    contract = load_feature_contract()
    return [contract["identifier"], *(f["name"] for f in contract["features"])]


def validate_blob_name(blob_name: str) -> None:
    if not blob_name or len(blob_name) > 255:
        raise CsvContractError("blobName is empty or longer than 255 characters")
    if not blob_name.lower().endswith(".csv"):
        raise CsvContractError("Only .csv files are accepted")
    if "/" in blob_name or "\\" in blob_name or ".." in blob_name:
        raise CsvContractError("Invalid blob name (path or traversal)")
    if not BLOB_NAME_PATTERN.fullmatch(blob_name):
        raise CsvContractError("Blob name contains unsupported characters")


def validate_size(size: int, max_bytes: int) -> None:
    if size <= 0:
        raise CsvContractError(f"Empty file (size={size})")
    if size > max_bytes:
        raise CsvContractError(
            f"File too large: {size} bytes, limit is {max_bytes} bytes (1 MiB)"
        )


def _parse_number(raw: str, *, field: str, integer: bool) -> int | float:
    text = raw.strip()
    try:
        value: int | float = int(text) if integer else float(text)
    except ValueError as exc:
        raise CsvContractError(f"row {field}: not a valid number") from exc
    if isinstance(value, float) and not math.isfinite(value):
        raise CsvContractError(f"row {field}: non-finite number")
    return value


def _validate_value(name: str, raw: str | None, spec: dict[str, Any]) -> Any:
    api_type = spec["api_type"]
    text = "" if raw is None else raw.strip()
    if text == "":
        if api_type == "number-or-null":
            return None
        raise CsvContractError(f"missing value for {name}")
    if spec["kind"] == "categorical":
        if text not in spec["allowed_values"]:
            raise CsvContractError(
                f"unexpected category for {name}; "
                f"(allowed: {', '.join(spec['allowed_values'])})"
            )
        return text
    value = _parse_number(text, field=name, integer=api_type == "integer")
    lower, upper = spec["allowed_range"]
    if not lower <= value <= upper:
        raise CsvContractError(f"{name} is outside [{lower}, {upper}]")
    return value


def parse_csv(
    payload: bytes,
    *,
    settings: Settings,
    blob_name: str = "upload.csv",
) -> list[dict[str, Any]]:
    """Return API-ready rows, or raise :class:`CsvContractError`.

    Blank lines are ignored. Extra columns are rejected because ``POST
    /predict/batch`` uses ``extra='forbid'``.
    """
    validate_size(len(payload), settings.max_csv_bytes)
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvContractError("File is not valid UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text))
    header = list(reader.fieldnames or [])
    expected = required_columns()
    if header != expected:
        missing = sorted(set(expected) - set(header))
        extra = sorted(set(header) - set(expected))
        raise CsvContractError(
            "Invalid CSV header: "
            + (f"missing columns {missing}; " if missing else "")
            + (f"unexpected columns ({len(extra)}); " if extra else "")
            + "expected exact column order"
        )

    contract = {feature["name"]: feature for feature in load_feature_contract()["features"]}
    identifier = load_feature_contract()["identifier"]
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, raw_row in enumerate(reader, start=2):
        if None in raw_row:
            raise CsvContractError(f"row {line_number}: more values than columns")
        if all((value is None or value.strip() == "") for value in raw_row.values()):
            continue  # blank-line policy: ignore
        if len(rows) >= settings.max_batch_rows:
            raise CsvContractError(
                f"Too many rows: limit is {settings.max_batch_rows} (1 MiB CSV cap)"
            )
        parsed: dict[str, Any] = {}
        for name, raw_value in raw_row.items():
            if name == identifier:
                customer_id = raw_value or ""
                if not 1 <= len(customer_id) <= 64 or not CUSTOMER_ID_PATTERN.fullmatch(customer_id):
                    errors.append(f"row {line_number}: invalid customerID")
                else:
                    parsed[name] = customer_id
                continue
            try:
                parsed[name] = _validate_value(name, raw_value, contract[name])
            except CsvContractError as exc:
                errors.append(f"row {line_number}: {exc.reason}")
                if len(errors) >= MAX_REJECTED_ERRORS:
                    break
        if errors and len(errors) >= MAX_REJECTED_ERRORS:
            break
        rows.append(parsed)

    if errors:
        raise CsvContractError("; ".join(errors))
    if not rows:
        raise CsvContractError(f"{blob_name}: no data rows")
    return rows
