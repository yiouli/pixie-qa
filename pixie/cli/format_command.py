"""``pixie format`` CLI command — convert trace logs into dataset entries.

Usage::

    pixie format --input trace.jsonl --output dataset_entry.json

Reads a JSONL trace file produced by ``pixie trace`` and converts it
into a valid dataset entry JSON object suitable for inclusion in a
dataset file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import JsonValue

from pixie.eval.evaluable import NamedData
from pixie.harness.runner import DatasetEntry
from pixie.instrumentation.models import InputDataLog, LLMSpanLog
from pixie.instrumentation.wrap import WrappedData


def _load_trace_log(
    input_path: Path,
) -> tuple[
    InputDataLog | None,
    list[WrappedData],
    list[LLMSpanLog],
    list[tuple[str, WrappedData | LLMSpanLog]],
]:
    """Parse a JSONL trace file into typed log records.

    Uses pydantic ``model_validate`` for each record type to ensure
    consistent deserialization.

    Args:
        input_path: Path to the JSONL trace file.

    Returns:
        A tuple of (entry_input, wrap_events, llm_spans, ordered_non_input)
        where *ordered_non_input* preserves the original file order for
        output/state wraps and LLM spans (used for building expectation).
    """
    entry_input: InputDataLog | None = None
    wrap_events: list[WrappedData] = []
    llm_spans: list[LLMSpanLog] = []
    ordered_non_input: list[tuple[str, WrappedData | LLMSpanLog]] = []

    with open(input_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            record_type = record.get("type")
            if record_type == "kwargs":
                entry_input = InputDataLog.model_validate(record)
            elif record_type == "wrap":
                wrapped = WrappedData.model_validate(record)
                wrap_events.append(wrapped)
                if wrapped.purpose in ("output", "state"):
                    ordered_non_input.append(("wrap", wrapped))
            elif record_type == "llm_span":
                span_log = LLMSpanLog.model_validate(record)
                llm_spans.append(span_log)
                ordered_non_input.append(("llm_span", span_log))

    return entry_input, wrap_events, llm_spans, ordered_non_input


def _wrap_to_named_data(event: WrappedData) -> NamedData:
    """Convert a :class:`WrappedData` to a :class:`NamedData`."""
    return NamedData(name=event.name, value=event.data)


def _llm_span_log_to_named_data(span: LLMSpanLog) -> NamedData:
    """Convert an :class:`LLMSpanLog` to a :class:`NamedData`.

    Serialises only non-None semantic fields (excludes ``type``).
    """
    dumped = span.model_dump(mode="json", exclude={"type"}, exclude_none=True)
    # Remove empty lists to keep output tidy
    dumped = {k: v for k, v in dumped.items() if v != []}
    model = span.request_model or span.response_model or "llm_call"
    name = f"llm_span_{model}"
    return NamedData(name=name, value=dumped)


def format_trace_to_entry(
    input_path: Path,
    output_path: Path,
) -> None:
    """Convert a trace log file into a dataset entry JSON file.

    The output is guaranteed to be a valid :class:`DatasetEntry` because
    it is constructed as a pydantic model and serialised with
    ``model_dump``.

    Args:
        input_path: Path to the JSONL trace file.
        output_path: Path to write the dataset entry JSON.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If the trace log has no usable data.
    """
    if not input_path.is_file():
        raise FileNotFoundError(f"Input trace file not found: {input_path}")

    entry_input, wrap_events, _llm_spans, ordered_non_input = _load_trace_log(
        input_path
    )

    # Build eval_input from wrap events with purpose='input'
    eval_input: list[NamedData] = [
        _wrap_to_named_data(w) for w in wrap_events if w.purpose == "input"
    ]

    # input_data is injected into eval_input at evaluation time by the
    # runner, so we don't duplicate it here.
    kwargs: dict[str, JsonValue] = entry_input.value if entry_input is not None else {}

    # Build expectation from output/state wraps and LLM spans, in log order
    expectation_items: list[NamedData] = []
    for record_type, record in ordered_non_input:
        if record_type == "wrap":
            assert isinstance(record, WrappedData)
            expectation_items.append(_wrap_to_named_data(record))
        elif record_type == "llm_span":
            assert isinstance(record, LLMSpanLog)
            expectation_items.append(_llm_span_log_to_named_data(record))

    expectation: JsonValue = None
    if expectation_items:
        expectation = [item.model_dump() for item in expectation_items]

    # Build the DatasetEntry pydantic model and serialise
    dataset_entry = DatasetEntry(
        input_data=kwargs,
        eval_input=eval_input,
        expectation=expectation,
        description=f"transformed from {input_path.name}",
        evaluators=["Factuality"],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset_entry.model_dump(mode="json"), f, indent=2, default=str)
        f.write("\n")


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``pixie format`` command.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="pixie format",
        description="Convert a trace log into a dataset entry JSON object",
    )
    parser.add_argument(
        "--input",
        required=True,
        dest="input_path",
        help="Path to the JSONL trace file (produced by 'pixie trace')",
    )
    parser.add_argument(
        "--output",
        required=True,
        dest="output_path",
        help="Path for the output dataset entry JSON file",
    )

    args = parser.parse_args(argv)
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)

    try:
        format_trace_to_entry(input_path, output_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
        return 1

    print(f"Dataset entry written to {output_path}")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
