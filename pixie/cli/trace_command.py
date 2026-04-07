"""``pixie trace`` CLI command — run a Runnable and capture trace output.

Usage::

    pixie trace --runnable path/to/file.py:MyRunnable \\
                --input kwargs.json \\
                --output trace.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import asdict

from pixie.instrumentation.llm_tracing import InstrumentationHandler, LLMSpan, add_handler
from pixie.instrumentation.wrap import TraceLogProcessor


class LLMTraceLogger(InstrumentationHandler):
    def __init__(self, trace_log_processor: TraceLogProcessor) -> None:
        self.trace_log_processor = trace_log_processor

    async def on_llm(self, span: LLMSpan) -> None:
        self.trace_log_processor.write_line(
            {
                "type": "llm_span",
                "operation": span.operation,
                "input_messages": [asdict(msg) for msg in span.input_messages],
                "output_messages": [asdict(msg) for msg in span.output_messages],
                "tool_definitions": [asdict(tool) for tool in span.tool_definitions],
            }
        )


def _run_trace(
    *,
    runnable: str,
    input_path: str,
    output_path: str,
) -> int:
    """Execute the trace: load kwargs, set up tracing, run the runnable.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    from pixie.harness.runner import load_input_kwargs, run_runnable
    from pixie.instrumentation.llm_tracing import enable_llm_tracing
    from pixie.instrumentation.wrap import logger_provider

    # Enable tracing via env so init() picks it up
    os.environ["PIXIE_TRACING"] = "1"
    os.environ["PIXIE_TRACE_OUTPUT"] = output_path

    try:
        kwargs = load_input_kwargs(input_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
        return 1

    # Set up trace log processor for wrap events, kwargs, and LLM spans.
    trace_logger = TraceLogProcessor(output_path)
    logger_provider.add_log_record_processor(trace_logger)

    # Initialize instrumentation (OTel, auto-instrumentors, etc.)
    enable_llm_tracing()
    add_handler(LLMTraceLogger(trace_logger))

    try:
        trace_logger.write_line({"type": "kwargs", "value": kwargs})
        asyncio.run(run_runnable(runnable, kwargs))
    except Exception as exc:
        print(f"Error running runnable: {exc}", file=sys.stderr)  # noqa: T201
        return 1

    # Flush pending spans
    from pixie.instrumentation.llm_tracing import flush

    flush()

    print(f"Trace written to {output_path}")  # noqa: T201
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``pixie trace`` command.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="pixie trace",
        description="Run a Runnable and capture trace output to a JSONL file",
    )
    parser.add_argument(
        "--runnable",
        required=True,
        help="Runnable reference in filepath:name format (e.g. 'app.py:MyRunnable')",
    )
    parser.add_argument(
        "--input",
        required=True,
        dest="input_path",
        help="Path to JSON file containing kwargs for the runnable",
    )
    parser.add_argument(
        "--output",
        required=True,
        dest="output_path",
        help="Path for the JSONL trace output file",
    )

    args = parser.parse_args(argv)

    return _run_trace(
        runnable=args.runnable,
        input_path=args.input_path,
        output_path=args.output_path,
    )


if __name__ == "__main__":
    sys.exit(main())
