import pytest

import api.inference as inf
from api.inference import ValidationError, validate_and_frame, predict_labels


def test_validate_and_frame_happy_path(sample_record_valid):
    df = validate_and_frame([sample_record_valid])
    assert df.shape[0] == 1
    assert not df.isna().any().any()


def test_validate_and_frame_missing_keys_raises(sample_record_valid):
    bad = dict(sample_record_valid)
    key_to_remove = next(iter(bad.keys()))
    bad.pop(key_to_remove)
    with pytest.raises(ValidationError):
        validate_and_frame([bad])


def test_validate_and_frame_non_numeric_raises(sample_record_valid):
    bad = dict(sample_record_valid)
    df = validate_and_frame([sample_record_valid])
    numeric_key = next(k for k in df.columns if df[k].dtype.kind in {"i", "u", "f"})
    bad[numeric_key] = "xx"
    with pytest.raises(ValidationError):
        validate_and_frame([bad])


def test_predict_labels_with_stub_bundle(monkeypatch, sample_record_valid):
    def fake_make_predictions(model, X, pp):  # noqa: ARG001
        return [0] * len(X)

    monkeypatch.setattr(inf, "make_predictions", fake_make_predictions)

    class DummyBundle:
        def __init__(self):
            self.preprocessor = object()
            self.model = object()

    df = validate_and_frame([sample_record_valid, sample_record_valid])
    out = predict_labels(DummyBundle(), df)
    assert out == [0, 0]
