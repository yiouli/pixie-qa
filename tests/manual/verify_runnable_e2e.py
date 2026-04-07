"""End-to-end verification: trace → format → test pipeline.

This script exercises the full Runnable protocol workflow:
1. ``pixie trace`` — run the chatbot Runnable and capture a trace
2. ``pixie format`` — convert the trace into a dataset entry
3. Wrap the entry into a dataset and run ``pixie test``

Usage::

    cd /home/yiouli/repo/pixie-qa
    uv run python tests/manual/verify_runnable_e2e.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_cmd(args: list[str], label: str) -> int:
    """Run a command and print its output."""
    print(f"\n{'=' * 60}")  # noqa: T201
    print(f"  {label}")  # noqa: T201
    print(f"  $ {' '.join(args)}")  # noqa: T201
    print(f"{'=' * 60}")  # noqa: T201
    result = subprocess.run(args, capture_output=False, text=True)
    return result.returncode


def main() -> int:
    """Run the e2e verification pipeline."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="pixie_runnable_e2e_"))
    print(f"Working directory: {tmp_dir}")  # noqa: T201

    # ── 1. Create input kwargs file ──────────────────────────────────────
    kwargs_file = tmp_dir / "kwargs.json"
    kwargs = {"user_message": "What are your business hours?", "customer_id": "C001"}
    kwargs_file.write_text(json.dumps(kwargs, indent=2))
    print(f"\n[1] Created kwargs file: {kwargs_file}")  # noqa: T201

    # ── 2. Run pixie trace ──────────────────────────────────────────────
    trace_output = tmp_dir / "trace.jsonl"
    rc = run_cmd(
        [
            sys.executable,
            "-m",
            "pixie.cli.main",
            "trace",
            "--runnable",
            "tests/manual/chatbot.py:ChatRunnable",
            "--input",
            str(kwargs_file),
            "--output",
            str(trace_output),
        ],
        "Step 2: pixie trace",
    )
    if rc != 0:
        print(f"ERROR: pixie trace failed with exit code {rc}")  # noqa: T201
        return 1

    # Print trace contents
    print(f"\nTrace file contents ({trace_output}):")  # noqa: T201
    for line in trace_output.read_text().strip().split("\n"):
        record = json.loads(line)
        print(
            f"  type={record.get('type')}, name={record.get('name', 'N/A')}, purpose={record.get('purpose', 'N/A')}"
        )  # noqa: T201, E501

    # ── 3. Run pixie format ─────────────────────────────────────────────
    entry_file = tmp_dir / "entry.json"
    rc = run_cmd(
        [
            sys.executable,
            "-m",
            "pixie.cli.main",
            "format",
            "--input",
            str(trace_output),
            "--output",
            str(entry_file),
        ],
        "Step 3: pixie format",
    )
    if rc != 0:
        print(f"ERROR: pixie format failed with exit code {rc}")  # noqa: T201
        return 1

    # Print formatted entry
    entry = json.loads(entry_file.read_text())
    print("\nFormatted entry:")  # noqa: T201
    print(json.dumps(entry, indent=2)[:500])  # noqa: T201

    # ── 4. Wrap entry into dataset and run pixie test ───────────────────
    # Replace evaluators with mock evaluators for testing
    entry["evaluators"] = [
        "tests/manual/mock_evaluators.py:SimpleFactualityEval",
    ]

    dataset = {
        "name": "runnable-e2e-test",
        "runnable": "tests/manual/chatbot.py:ChatRunnable",
        "entries": [entry],
    }
    dataset_file = tmp_dir / "dataset.json"
    dataset_file.write_text(json.dumps(dataset, indent=2))
    print(f"\n[4] Created dataset file: {dataset_file}")  # noqa: T201

    rc = run_cmd(
        [
            sys.executable,
            "-m",
            "pixie.cli.main",
            "test",
            str(dataset_file),
            "--no-open",
        ],
        "Step 4: pixie test",
    )
    if rc != 0:
        print(
            f"\nWARNING: pixie test returned exit code {rc} (may have failing evals)"
        )  # noqa: T201

    print(f"\n{'=' * 60}")  # noqa: T201
    print("  E2E verification complete!")  # noqa: T201
    print(f"  Artifacts in: {tmp_dir}")  # noqa: T201
    print(f"{'=' * 60}")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
