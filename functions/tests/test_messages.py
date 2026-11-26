import json

import pytest

from src.messages import InferenceRequest, MessageError, rejection_reason

RAW = {
    "blobName": "batch_01.csv",
    "etag": '0x8DC"A1',
    "size": 12345,
    "enqueuedAt": "2026-11-24T10:00:00Z",
}


def test_round_trip() -> None:
    message = InferenceRequest.from_json(json.dumps(RAW))
    assert message == InferenceRequest.from_json(json.dumps(RAW))
    assert json.loads(message.to_json()) == RAW
    assert message.idempotency_key.startswith("batch_01-")
    assert len(message.idempotency_key) == 9 + 16


def test_idempotency_key_is_stable_and_version_scoped() -> None:
    def make(data):
        return InferenceRequest.from_json(json.dumps(data))
    first = make(RAW).idempotency_key
    assert first == make(RAW).idempotency_key
    assert first != make({**RAW, "etag": "0x8DCB2"}).idempotency_key
    assert first != make({**RAW, "blobName": "other.csv"}).idempotency_key
    assert all(character.isalnum() or character in "._-" for character in first)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data | {"extra": 1},
        lambda data: {key: value for key, value in data.items() if key != "size"},
        lambda data: data | {"size": "12345"},
        lambda data: data | {"etag": ""},
        lambda data: data | {"blobName": "batch.txt"},
        lambda data: data | {"enqueuedAt": "not-a-date"},
    ],
)
def test_invalid_messages(mutation) -> None:
    with pytest.raises(MessageError):
        InferenceRequest.from_json(json.dumps(mutation(RAW)))


def test_non_json_message() -> None:
    with pytest.raises(MessageError):
        InferenceRequest.from_json("not json")


def test_rejection_reason_is_plain_json() -> None:
    reason = rejection_reason("batch.csv", "bad column")
    assert json.loads(json.dumps(reason)) == {
        "blobName": "batch.csv",
        "reason": "bad column",
        "status": "rejected",
    }
