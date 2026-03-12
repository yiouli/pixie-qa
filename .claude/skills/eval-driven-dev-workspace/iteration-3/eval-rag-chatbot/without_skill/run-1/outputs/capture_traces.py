"""Capture traces from the RAG chatbot and save them to a pixie dataset.

Run with:
    PYTHONPATH=/home/yiouli/repo/pixie-qa python capture_traces.py
"""

import os
import sys

# Ensure we run from the project directory so dataset files are written here
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)
os.environ.setdefault("PIXIE_DATASET_DIR", os.path.join(PROJECT_DIR, "pixie_datasets"))

import pixie.instrumentation as px
from pixie.dataset.store import DatasetStore
from pixie.evals.trace_capture import capture_traces
from pixie.storage.evaluable import Evaluable

# Import the instrumented chatbot functions
sys.path.insert(0, PROJECT_DIR)
from chatbot import answer_question

DATASET_NAME = "rag-chatbot-traces"

# Question → expected answer pairs
TEST_CASES = [
    ("What is the capital of France?", "Paris is the capital of France."),
    ("What language do people speak in Germany?", "German is spoken in Germany and Austria."),
    ("What is the population of France?", "France has a population of about 68 million."),
    ("What currency does Germany use?", "Germany also uses the Euro (EUR)."),
]


def run_and_collect() -> list[Evaluable]:
    """Run the chatbot for each question, capture traces, collect Evaluable items."""
    evaluables: list[Evaluable] = []

    for question, expected in TEST_CASES:
        with capture_traces() as handler:
            result = answer_question(question)

        print(f"Q: {question}")
        print(f"A: {result}")
        print(f"Expected: {expected}")
        print(f"Spans captured: {len(handler.spans)}")
        print()

        # Find the root span (answer_question) to build the Evaluable
        root_spans = [s for s in handler.spans if hasattr(s, "name") and s.name == "answer_question"]
        if root_spans:
            span = root_spans[0]
            evaluable = Evaluable(
                eval_input=question,
                eval_output=result,
                expected_output=expected,
                eval_metadata={"span_name": span.name, "trace_id": span.trace_id},
            )
        else:
            evaluable = Evaluable(
                eval_input=question,
                eval_output=result,
                expected_output=expected,
            )
        evaluables.append(evaluable)

    return evaluables


def save_dataset(evaluables: list[Evaluable]) -> None:
    """Save the collected evaluables to a named dataset."""
    dataset_dir = os.environ.get("PIXIE_DATASET_DIR", os.path.join(PROJECT_DIR, "pixie_datasets"))
    store = DatasetStore(dataset_dir=dataset_dir)

    # Delete existing dataset if present so we can recreate it
    try:
        store.delete(DATASET_NAME)
        print(f"Deleted existing dataset '{DATASET_NAME}'")
    except FileNotFoundError:
        pass

    dataset = store.create(DATASET_NAME, items=evaluables)
    print(f"Dataset '{dataset.name}' created with {len(dataset.items)} items.")
    print(f"Dataset saved to: {dataset_dir}/{DATASET_NAME.replace(' ', '-')}.json")


if __name__ == "__main__":
    print("=== Capturing traces ===\n")
    evaluables = run_and_collect()
    print("=== Saving dataset ===\n")
    save_dataset(evaluables)
    print("\nDone.")
