from pathlib import Path

import pytest

from src.config import Settings
from src.contract import (
    CsvContractError,
    load_feature_contract,
    parse_csv,
    required_columns,
    validate_blob_name,
    validate_size,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "valid_batch.csv"
SETTINGS = Settings()


def payload() -> bytes:
    return FIXTURE.read_bytes()


def test_feature_contract_is_the_shared_21_columns() -> None:
    contract = load_feature_contract()
    assert contract["feature_count"] == 21
    assert len(contract["features"]) == 21
    assert len(required_columns()) == 22
    assert required_columns()[0] == "customerID"
    assert {"numAdminTickets", "numTechTickets"}.issubset(required_columns())
    assert "Churn" not in required_columns()


@pytest.mark.parametrize("name", ["batch_01.csv", "A-B.C.csv"])
def test_valid_blob_names(name: str) -> None:
    validate_blob_name(name)


@pytest.mark.parametrize(
    "name", ["batch.txt", "sub/batch.csv", "../batch.csv", "", "a b.csv"]
)
def test_invalid_blob_names(name: str) -> None:
    with pytest.raises(CsvContractError):
        validate_blob_name(name)


def test_size_limits() -> None:
    validate_size(1024, SETTINGS.max_csv_bytes)
    with pytest.raises(CsvContractError, match="too large"):
        validate_size(SETTINGS.max_csv_bytes + 1, SETTINGS.max_csv_bytes)
    with pytest.raises(CsvContractError, match="Empty"):
        validate_size(0, SETTINGS.max_csv_bytes)


def test_valid_csv_is_coerced_for_the_api() -> None:
    rows = parse_csv(payload(), settings=SETTINGS, blob_name="valid_batch.csv")
    assert len(rows) == 3
    assert rows[0]["customerID"] == "7590-VHVEG"
    assert rows[0]["SeniorCitizen"] == 0
    assert rows[0]["MonthlyCharges"] == 29.85
    assert rows[0]["TotalCharges"] == 29.85
    assert rows[1]["numAdminTickets"] == 2
    assert set(rows[0]) == set(required_columns())


def test_blank_lines_are_ignored() -> None:
    text = payload().decode()
    lines = text.splitlines()
    data = "\n".join([lines[0], lines[1], "", lines[2], "   ", lines[3], ""])
    rows = parse_csv(data.encode(), settings=SETTINGS)
    assert len(rows) == 3


def test_blank_total_charges_becomes_none() -> None:
    text = payload().decode().replace("56.95,1889.5,2,0", "56.95,,2,0")
    rows = parse_csv(text.encode(), settings=SETTINGS)
    assert rows[1]["TotalCharges"] is None


@pytest.mark.parametrize(
    "mutation,message",
    [
        (lambda text: text.replace("customerID,", "id,"), "missing columns"),
        (lambda text: text.replace("customerID,", "customerID,extra,"), "unexpected columns"),
        (lambda text: text.replace(",29.85,29.85,", ",abc,29.85,"), "not a valid number"),
        (lambda text: text.replace(",1,No,No phone", ",999,No,No phone"), "outside"),
        (lambda text: text.replace(",Female,0,", ",Other,0,"), "unexpected category"),
        (lambda text: text.replace(",0,1\n", ",NaN,1\n"), "not a valid number"),
    ],
)
def test_invalid_values_are_rejected(mutation, message: str) -> None:
    text = mutation(payload().decode())
    with pytest.raises(CsvContractError, match=message):
        parse_csv(text.encode(), settings=SETTINGS)


def test_blank_required_numeric_is_rejected() -> None:
    text = payload().decode().replace(",0,No,Yes,1,", ",0,No,Yes,,", 1)
    with pytest.raises(CsvContractError, match="missing value"):
        parse_csv(text.encode(), settings=SETTINGS)


def test_row_cap_is_enforced() -> None:
    text = payload().decode()
    header, *lines = text.splitlines()
    data = "\n".join([header, *(lines * 40)])
    small = Settings(max_batch_rows=5)
    with pytest.raises(CsvContractError, match="Too many rows"):
        parse_csv(data.encode(), settings=small)


@pytest.mark.parametrize("bad_id", ["7590 VHVEG", "a/b", " lead", "trail ", "é123", "x" * 65])
def test_invalid_customer_id_rejected_locally_without_echo(bad_id):
    data = payload().decode().replace("7590-VHVEG", bad_id, 1).encode()
    with pytest.raises(CsvContractError, match="invalid customerID") as exc:
        parse_csv(data, settings=SETTINGS)
    assert bad_id not in str(exc.value)


def test_customer_id_ascii_pattern_accepts_dot_underscore_hyphen():
    data = payload().decode().replace("7590-VHVEG", "id.A_b-1", 1).encode()
    assert parse_csv(data, settings=SETTINGS)[0]["customerID"] == "id.A_b-1"
