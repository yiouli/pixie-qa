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
    from pixie.evals.run_utils import load_input_kwargs, run_runnable
    from pixie.instrumentation.observation import init
    from pixie.instrumentation.trace_writer import TraceFileWriter, set_trace_writer

    # Enable tracing via env so init() picks it up
    os.environ["PIXIE_TRACING"] = "1"
    os.environ["PIXIE_TRACE_OUTPUT"] = output_path

    try:
        kwargs = load_input_kwargs(input_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)  # noqa: T201
        return 1

    # Set up trace writer before init (init also sets one up, but we
    # want to ensure the output path is correct)
    writer = TraceFileWriter(output_path)
    set_trace_writer(writer)

    # Initialize instrumentation (OTel, auto-instrumentors, etc.)
    init()

    try:
        asyncio.run(run_runnable(runnable, kwargs))
    except Exception as exc:
        print(f"Error running runnable: {exc}", file=sys.stderr)  # noqa: T201
        return 1

    # Flush pending spans
    from pixie.instrumentation.observation import flush

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
