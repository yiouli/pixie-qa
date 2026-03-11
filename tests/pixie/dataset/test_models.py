"""Tests for pixie.dataset.models — Dataset Pydantic model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pixie.dataset.models import Dataset
from pixie.storage.evaluable import UNSET, Evaluable


class TestDatasetConstruction:
    """Tests for Dataset model construction."""

    def test_construction_with_name_and_items(self) -> None:
        items = (
            Evaluable(eval_input="q1", expected_output="a1"),
            Evaluable(eval_input="q2", expected_output="a2"),
        )
        ds = Dataset(name="my-test", items=items)
        assert ds.name == "my-test"
        assert len(ds.items) == 2
        assert ds.items[0].eval_input == "q1"

    def test_construction_with_name_only(self) -> None:
        ds = Dataset(name="empty-set")
        assert ds.name == "empty-set"
        assert ds.items == ()

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            Dataset(name="")

    def test_frozen(self) -> None:
        ds = Dataset(name="frozen-test")
        with pytest.raises(ValidationError):
            ds.name = "mutated"  # type: ignore[misc]


class TestDatasetSerialisation:
    """Tests for Dataset model_dump / model_validate round-trip."""

    def test_round_trip(self) -> None:
        items = (
            Evaluable(eval_input="What is 2+2?", expected_output="4"),
            Evaluable(eval_input="Capital of France?", expected_output="Paris"),
        )
        ds = Dataset(name="qa-set", items=items)
        data = ds.model_dump(mode="json")
        restored = Dataset.model_validate(data)
        assert restored == ds
        assert restored.items[0].expected_output == "4"

    def test_round_trip_preserves_unset(self) -> None:
        ds = Dataset(name="no-expected", items=(Evaluable(eval_input="q"),))
        data = ds.model_dump(mode="json")
        restored = Dataset.model_validate(data)
        assert restored.items[0].expected_output is UNSET

    def test_empty_items_round_trip(self) -> None:
        ds = Dataset(name="empty")
        data = ds.model_dump(mode="json")
        restored = Dataset.model_validate(data)
        assert restored.items == ()
