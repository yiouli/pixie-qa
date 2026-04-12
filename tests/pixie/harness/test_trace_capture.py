"""Tests for pixie.harness.trace_capture — unified per-entry trace capture."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from pixie.harness.trace_capture import (
    EntryTraceCollector,
    EntryTraceLogProcessor,
    current_entry_index,
    get_active_collector,
    record_input_data,
    set_active_collector,
)
from pixie.instrumentation.llm_tracing import (
    LLMSpan,
    _DeliveryQueue,
    _HandlerRegistry,
)


def _make_span(*, model: str = "gpt-4o", started_at: datetime | None = None) -> LLMSpan:
    """Create a minimal LLMSpan fixture."""
    now = started_at or datetime.now(timezone.utc)
    return LLMSpan(
        span_id="abcdef0123456789",
        trace_id="00000000000000000000000000000001",
        parent_span_id=None,
        started_at=now,
        ended_at=now,
        duration_ms=42.0,
        operation="chat",
        provider="openai",
        request_model=model,
        response_model=model,
        input_tokens=10,
        output_tokens=20,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        request_temperature=0.7,
        request_max_tokens=100,
        request_top_p=None,
        finish_reasons=("stop",),
        response_id=None,
        output_type=None,
        error_type=None,
        input_messages=(),
        output_messages=(),
        tool_definitions=(),
    )


def _read_jsonl(path: Path) -> list[dict]:  # type: ignore[type-arg]
    """Parse all JSON lines from a file."""
    return [
        json.loads(line)
        for line in path.read_text().strip().split("\n")
        if line.strip()
    ]


class TestEntryTraceCollector:
    """Tests for EntryTraceCollector."""

    def test_on_llm_accumulates_by_entry_index(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        span_a = _make_span()
        span_b = _make_span(model="claude-3")

        current_entry_index.set(0)
        asyncio.run(collector.on_llm(span_a))

        current_entry_index.set(1)
        asyncio.run(collector.on_llm(span_b))

        out0 = tmp_path / "entry-0.jsonl"
        collector.write_entry_trace(0, str(out0))
        lines0 = _read_jsonl(out0)
        llm0 = [r for r in lines0 if r.get("type") == "llm_span_trace"]
        assert len(llm0) == 1
        assert llm0[0]["request_model"] == "gpt-4o"

        out1 = tmp_path / "entry-1.jsonl"
        collector.write_entry_trace(1, str(out1))
        lines1 = _read_jsonl(out1)
        llm1 = [r for r in lines1 if r.get("type") == "llm_span_trace"]
        assert len(llm1) == 1
        assert llm1[0]["request_model"] == "claude-3"

    def test_on_llm_drops_without_entry_context(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        current_entry_index.set(None)
        asyncio.run(collector.on_llm(_make_span()))

        out = tmp_path / "entry-0.jsonl"
        count = collector.write_entry_trace(0, str(out))
        assert count == 0

    def test_set_input_data_written_first(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        collector.set_input_data(0, {"user_message": "hello"})

        current_entry_index.set(0)
        asyncio.run(collector.on_llm(_make_span()))

        out = tmp_path / "entry-0.jsonl"
        collector.write_entry_trace(0, str(out))
        lines = _read_jsonl(out)

        # First record should be kwargs
        assert lines[0]["type"] == "kwargs"
        assert lines[0]["value"]["user_message"] == "hello"
        # Second record should be LLM span
        assert lines[1]["type"] == "llm_span_trace"

    def test_add_wrap_event(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        collector.add_wrap_event(
            0,
            {
                "type": "wrap",
                "name": "profile",
                "purpose": "input",
                "data": {"name": "Alice"},
                "captured_at": "2025-01-01T00:00:01Z",
            },
        )

        out = tmp_path / "entry-0.jsonl"
        count = collector.write_entry_trace(0, str(out))
        assert count == 1
        lines = _read_jsonl(out)
        assert lines[0]["type"] == "wrap"
        assert lines[0]["name"] == "profile"
        assert lines[0]["purpose"] == "input"

    def test_write_entry_trace_full_timeline(self, tmp_path: Path) -> None:
        """Full trace contains kwargs + wrap events + LLM spans in order."""
        collector = EntryTraceCollector()
        collector.set_input_data(0, {"q": "test"})

        # Add wrap event with early timestamp
        collector.add_wrap_event(
            0,
            {
                "type": "wrap",
                "name": "input_data",
                "purpose": "input",
                "captured_at": "2025-01-01T00:00:01Z",
            },
        )

        # Add LLM span with later start time
        span = _make_span()
        current_entry_index.set(0)
        asyncio.run(collector.on_llm(span))

        # Add wrap event with latest timestamp
        collector.add_wrap_event(
            0,
            {
                "type": "wrap",
                "name": "output_data",
                "purpose": "output",
                "captured_at": "2025-12-31T23:59:59Z",
            },
        )

        out = tmp_path / "entry-0.jsonl"
        count = collector.write_entry_trace(0, str(out))
        assert count == 4  # kwargs + 2 wraps + 1 LLM

        lines = _read_jsonl(out)
        assert lines[0]["type"] == "kwargs"
        assert lines[1]["type"] == "wrap"
        assert lines[1]["name"] == "input_data"
        # LLM span and output wrap order depends on timestamps
        types = [rec["type"] for rec in lines[2:]]
        assert "llm_span_trace" in types
        assert "wrap" in types

    def test_write_entry_trace_empty(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        out = tmp_path / "traces" / "entry-0.jsonl"
        count = collector.write_entry_trace(99, str(out))
        assert count == 0
        assert out.exists()
        assert out.read_text() == ""

    def test_write_entry_trace_removes_collected(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        collector.set_input_data(0, {"x": 1})
        current_entry_index.set(0)
        asyncio.run(collector.on_llm(_make_span()))

        out1 = tmp_path / "entry-0.jsonl"
        collector.write_entry_trace(0, str(out1))

        # Second write should produce empty file
        out2 = tmp_path / "entry-0b.jsonl"
        count = collector.write_entry_trace(0, str(out2))
        assert count == 0


class TestModuleLevelCollector:
    """Tests for module-level active collector functions."""

    def test_set_and_get_active_collector(self) -> None:
        collector = EntryTraceCollector()
        set_active_collector(collector)
        assert get_active_collector() is collector
        set_active_collector(None)
        assert get_active_collector() is None

    def test_record_input_data_routes_to_collector(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        set_active_collector(collector)
        try:
            record_input_data(0, {"msg": "hi"})

            out = tmp_path / "entry-0.jsonl"
            collector.write_entry_trace(0, str(out))
            lines = _read_jsonl(out)
            assert lines[0]["type"] == "kwargs"
            assert lines[0]["value"]["msg"] == "hi"
        finally:
            set_active_collector(None)

    def test_record_input_data_noop_without_collector(self) -> None:
        set_active_collector(None)
        # Should not raise
        record_input_data(0, {"msg": "hi"})


class TestEntryTraceLogProcessor:
    """Tests for EntryTraceLogProcessor."""

    def test_on_emit_routes_wrap_event(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        set_active_collector(collector)
        processor = EntryTraceLogProcessor()

        try:
            current_entry_index.set(0)

            # Create a mock log record
            class _Body:
                pass

            class _LogRecord:
                def __init__(self, body: dict) -> None:  # type: ignore[type-arg]
                    self.body = body

            class _ReadWriteLogRecord:
                def __init__(self, body: dict) -> None:  # type: ignore[type-arg]
                    self.log_record = _LogRecord(body)

            wrap_body = {
                "type": "wrap",
                "name": "profile",
                "purpose": "input",
                "data": {"name": "Bob"},
            }
            processor.on_emit(_ReadWriteLogRecord(wrap_body))  # type: ignore[arg-type]

            out = tmp_path / "entry-0.jsonl"
            collector.write_entry_trace(0, str(out))
            lines = _read_jsonl(out)
            assert len(lines) == 1
            assert lines[0]["type"] == "wrap"
            assert lines[0]["name"] == "profile"
            assert "captured_at" in lines[0]
        finally:
            set_active_collector(None)

    def test_on_emit_ignores_non_wrap(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        set_active_collector(collector)
        processor = EntryTraceLogProcessor()

        try:
            current_entry_index.set(0)

            class _LogRecord:
                def __init__(self, body: dict) -> None:  # type: ignore[type-arg]
                    self.body = body

            class _ReadWriteLogRecord:
                def __init__(self, body: dict) -> None:  # type: ignore[type-arg]
                    self.log_record = _LogRecord(body)

            processor.on_emit(_ReadWriteLogRecord({"type": "other"}))  # type: ignore[arg-type]

            out = tmp_path / "entry-0.jsonl"
            count = collector.write_entry_trace(0, str(out))
            assert count == 0
        finally:
            set_active_collector(None)

    def test_on_emit_drops_without_entry_context(self, tmp_path: Path) -> None:
        collector = EntryTraceCollector()
        set_active_collector(collector)
        processor = EntryTraceLogProcessor()

        try:
            current_entry_index.set(None)

            class _LogRecord:
                def __init__(self, body: dict) -> None:  # type: ignore[type-arg]
                    self.body = body

            class _ReadWriteLogRecord:
                def __init__(self, body: dict) -> None:  # type: ignore[type-arg]
                    self.log_record = _LogRecord(body)

            processor.on_emit(
                _ReadWriteLogRecord({"type": "wrap", "name": "x", "purpose": "input"})  # type: ignore[arg-type]
            )

            out = tmp_path / "entry-0.jsonl"
            count = collector.write_entry_trace(0, str(out))
            assert count == 0
        finally:
            set_active_collector(None)


class TestDeliveryQueueContextPropagation:
    """Integration test: LLM spans submitted through _DeliveryQueue preserve
    the current_entry_index ContextVar so EntryTraceCollector receives them."""

    def test_llm_span_routed_to_correct_entry_via_queue(self, tmp_path: Path) -> None:
        """Submit an LLMSpan through the real _DeliveryQueue pipeline and
        verify EntryTraceCollector captures it under the correct entry index."""
        collector = EntryTraceCollector()
        collector.set_input_data(0, {"q": "hello"})

        registry = _HandlerRegistry()
        registry.add(collector)
        dq = _DeliveryQueue(registry)

        span = _make_span(model="gpt-4o")

        # Set entry index on *this* thread (simulates the runner setting it
        # before the app calls the LLM).
        token = current_entry_index.set(0)
        try:
            dq.submit(span)
            dq.flush()
        finally:
            current_entry_index.reset(token)

        out = tmp_path / "entry-0.jsonl"
        count = collector.write_entry_trace(0, str(out))
        lines = _read_jsonl(out)

        # Should contain kwargs + the LLM span
        assert count == 2
        assert lines[0]["type"] == "kwargs"
        llm_records = [r for r in lines if r.get("type") == "llm_span_trace"]
        assert len(llm_records) == 1
        assert llm_records[0]["request_model"] == "gpt-4o"

    def test_llm_span_dropped_when_no_entry_context(self, tmp_path: Path) -> None:
        """An LLMSpan submitted without current_entry_index is silently dropped."""
        collector = EntryTraceCollector()

        registry = _HandlerRegistry()
        registry.add(collector)
        dq = _DeliveryQueue(registry)

        token = current_entry_index.set(None)
        try:
            dq.submit(_make_span())
            dq.flush()
        finally:
            current_entry_index.reset(token)

        out = tmp_path / "entry-0.jsonl"
        count = collector.write_entry_trace(0, str(out))
        assert count == 0

    def test_concurrent_entries_routed_correctly(self, tmp_path: Path) -> None:
        """Two spans submitted with different entry indices land in the
        correct per-entry buckets."""
        collector = EntryTraceCollector()
        collector.set_input_data(0, {"q": "first"})
        collector.set_input_data(1, {"q": "second"})

        registry = _HandlerRegistry()
        registry.add(collector)
        dq = _DeliveryQueue(registry)

        span_a = _make_span(model="gpt-4o")
        span_b = _make_span(model="claude-3")

        token = current_entry_index.set(0)
        try:
            dq.submit(span_a)
        finally:
            current_entry_index.reset(token)

        token = current_entry_index.set(1)
        try:
            dq.submit(span_b)
        finally:
            current_entry_index.reset(token)

        dq.flush()

        out0 = tmp_path / "entry-0.jsonl"
        collector.write_entry_trace(0, str(out0))
        lines0 = _read_jsonl(out0)
        llm0 = [r for r in lines0 if r.get("type") == "llm_span_trace"]
        assert len(llm0) == 1
        assert llm0[0]["request_model"] == "gpt-4o"

        out1 = tmp_path / "entry-1.jsonl"
        collector.write_entry_trace(1, str(out1))
        lines1 = _read_jsonl(out1)
        llm1 = [r for r in lines1 if r.get("type") == "llm_span_trace"]
        assert len(llm1) == 1
        assert llm1[0]["request_model"] == "claude-3"
