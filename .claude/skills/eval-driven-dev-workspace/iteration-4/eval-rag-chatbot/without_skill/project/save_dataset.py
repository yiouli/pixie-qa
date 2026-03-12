"""Save captured traces to a pixie Dataset.

Run this script after chatbot_instrumented.py has been executed so that
the SQLite database (pixie_observations.db) is populated.

Usage:
    PYTHONPATH=/home/yiouli/repo/pixie-qa python save_dataset.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.environ.get("PIXIE_PATH", "/home/yiouli/repo/pixie-qa"))

from piccolo.engine.sqlite import SQLiteEngine

from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable, as_evaluable
from pixie.storage.store import ObservationStore

DATASET_NAME = "rag-chatbot-traces"
DB_PATH = os.path.join(os.path.dirname(__file__), "pixie_observations.db")
DATASET_DIR = os.path.join(os.path.dirname(__file__), "pixie_datasets")

# Expected answers for each question (used as reference outputs in evals)
EXPECTED_ANSWERS: dict[str, str] = {
    "What is the capital of France?": "Paris is the capital of France.",
    "What language do people speak in Germany?": "French is spoken in France.",
    "What is the population of France?": "France has a population of about 68 million.",
    "What currency does Germany use?": "France uses the Euro (EUR).",
}


async def main() -> None:
    engine = SQLiteEngine(path=DB_PATH)
    store = ObservationStore(engine=engine)

    # List all traces
    traces = await store.list_traces()
    print(f"Found {len(traces)} trace(s) in {DB_PATH}")

    evaluables: list[Evaluable] = []
    for trace_summary in traces:
        trace_id = trace_summary["trace_id"]
        spans = await store.get_by_name("answer_question", trace_id=trace_id)
        for span in spans:
            ev = as_evaluable(span)
            # Try to extract a string input for lookup
            raw_input = ev.eval_input
            if isinstance(raw_input, dict):
                question = raw_input.get("question", "")
            else:
                question = str(raw_input) if raw_input else ""

            expected = EXPECTED_ANSWERS.get(question)
            ev_with_expected = Evaluable(
                eval_input=ev.eval_input,
                eval_output=ev.eval_output,
                eval_metadata=ev.eval_metadata,
                expected_output=expected,
            )
            evaluables.append(ev_with_expected)
            print(f"  Captured: Q={question!r} -> A={ev.eval_output!r}")

    if not evaluables:
        print("No answer_question spans found. Did you run chatbot_instrumented.py first?")
        sys.exit(1)

    dataset_store = DatasetStore(dataset_dir=DATASET_DIR)

    # Remove existing dataset if present
    try:
        dataset_store.delete(DATASET_NAME)
        print(f"Deleted existing dataset {DATASET_NAME!r}")
    except FileNotFoundError:
        pass

    dataset = dataset_store.create(DATASET_NAME, items=evaluables)
    print(f"\nSaved dataset {DATASET_NAME!r} with {len(dataset.items)} item(s) to {DATASET_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
