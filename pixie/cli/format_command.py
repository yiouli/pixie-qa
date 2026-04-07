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
from typing import Any

from pixie.storage.evaluable import NamedData, TestCase


def _load_trace_log(
    input_path: Path,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse a JSONL trace file into kwargs, wrap events, and LLM spans.

    Args:
        input_path: Path to the JSONL trace file.

    Returns:
        A tuple of (kwargs_dict, wrap_events, llm_spans) where each
        wrap_event and llm_span is the raw parsed dict preserving order.
    """
    kwargs: dict[str, Any] | None = None
    wrap_events: list[dict[str, Any]] = []
    llm_spans: list[dict[str, Any]] = []

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
                kwargs = record.get("value", {})
            elif record_type == "wrap":
                wrap_events.append(record)
            elif record_type == "llm_span":
                llm_spans.append(record)

    return kwargs, wrap_events, llm_spans


def _wrap_to_named_data(event: dict[str, Any]) -> NamedData:
    """Convert a wrap event dict to a NamedData."""
    return NamedData(
        name=event.get("name", "unknown"),
        value=event.get("data"),
    )


def _llm_span_to_named_data(span: dict[str, Any]) -> NamedData:
    """Convert an LLM span dict to a NamedData, stripping metadata-like fields.

    Keeps semantically meaningful fields: model, messages, tool definitions.
    Removes timing, IDs, token counts, and other metadata.
    """
    # Fields to keep for evaluation purposes
    keep_fields = {
        "operation",
        "provider",
        "request_model",
        "response_model",
        "input_messages",
        "output_messages",
        "tool_definitions",
        "finish_reasons",
        "output_type",
        "error_type",
    }
    filtered: dict[str, Any] = {
        k: v for k, v in span.items() if k in keep_fields and v is not None
    }
    # Use a descriptive name based on model if available
    model = span.get("request_model") or span.get("response_model") or "llm_call"
    name = f"llm_span_{model}"
    return NamedData(name=name, value=filtered)


def format_trace_to_entry(
    input_path: Path,
    output_path: Path,
) -> None:
    """Convert a trace log file into a dataset entry JSON file.

    Args:
        input_path: Path to the JSONL trace file.
        output_path: Path to write the dataset entry JSON.

    Raises:
        FileNotFoundError: If the input file does not exist.
        ValueError: If the trace log has no usable data.
    """
    if not input_path.is_file():
        raise FileNotFoundError(f"Input trace file not found: {input_path}")

    kwargs, wrap_events, llm_spans = _load_trace_log(input_path)

    # Build eval_input from wrap events with purpose='input'
    eval_input: list[NamedData] = []
    for event in wrap_events:
        if event.get("purpose") == "input":
            eval_input.append(_wrap_to_named_data(event))

    if not eval_input:
        # Fall back: use all entry-purpose wraps as input
        for event in wrap_events:
            if event.get("purpose") == "entry":
                eval_input.append(_wrap_to_named_data(event))

    if not eval_input:
        raise ValueError(
            "No input data found in trace log. "
            "Expected wrap events with purpose='input' or 'entry'."
        )

    # Build expectation from output/state wraps and LLM spans, in log order
    # We track the order by maintaining a combined list
    expectation_items: list[NamedData] = []

    # Build an ordered list of all records that belong in expectation
    # Re-read the file to preserve original order between wraps and spans
    ordered_records: list[tuple[str, dict[str, Any]]] = []
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
            purpose = record.get("purpose")
            if record_type == "wrap" and purpose in ("output", "state"):
                ordered_records.append(("wrap", record))
            elif record_type == "llm_span":
                ordered_records.append(("llm_span", record))

    for record_type, record in ordered_records:
        if record_type == "wrap":
            expectation_items.append(_wrap_to_named_data(record))
        elif record_type == "llm_span":
            expectation_items.append(_llm_span_to_named_data(record))

    # Build the expectation value
    expectation: Any = None
    if expectation_items:
        expectation = [item.model_dump() for item in expectation_items]

    # Build test_case
    test_case = TestCase(
        eval_input=eval_input,
        expectation=expectation,
        description=f"transformed from {input_path.name}",
    )

    # Build the dataset entry
    entry: dict[str, Any] = {
        "entry_kwargs": kwargs if kwargs is not None else {},
        "test_case": test_case.model_dump(mode="json"),
        "evaluators": ["Factuality"],
    }

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, default=str)
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
