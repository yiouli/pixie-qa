"""
Build the eval dataset for the RAG chatbot programmatically.

Run this script once to populate the dataset:
    python build_dataset.py

This uses the pixie DatasetStore + Evaluable API to create a golden set
without requiring a live app run (no API keys needed).
"""

from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

DATASET_NAME = "rag-golden-set"

# Each item: (question, expected_answer, notes)
# expected_answer is what a correct RAG system should return (used by FactualityEval)
ITEMS = [
    # --- Normal cases: question matches a retrieval keyword ---
    (
        {"question": "What is the capital of France?"},
        "Paris",
        "Basic capital question — context contains the answer directly",
    ),
    (
        {"question": "What is the capital of Germany?"},
        "Berlin",
        "Basic capital question — context contains the answer directly",
    ),
    (
        {"question": "What language do people speak in France?"},
        "French",
        "Language question — context says 'French is spoken in France'",
    ),
    (
        {"question": "What language do people speak in Germany?"},
        "German",
        "Language question — context says 'German is spoken in Germany and Austria'",
    ),
    (
        {"question": "What is the population of France?"},
        "About 68 million",
        "Population question — context has exact figure",
    ),
    (
        {"question": "What is the population of Germany?"},
        "About 84 million",
        "Population question — context has exact figure",
    ),
    # --- Indirect/multi-hop case ---
    (
        {"question": "What languages are spoken in Austria?"},
        "German",
        "Austria not in docs directly, but context says German is spoken in Germany AND Austria",
    ),
    # --- No-context / out-of-domain case ---
    (
        {"question": "What is the capital of Japan?"},
        "I don't know based on the provided context",
        "Out-of-domain: no relevant docs retrieved — model should admit it doesn't know",
    ),
]


def build():
    store = DatasetStore()

    # Create dataset (idempotent — delete first if re-running)
    existing = store.list()
    if DATASET_NAME in existing:
        print(f"Dataset '{DATASET_NAME}' already exists — deleting and rebuilding.")
        store.delete(DATASET_NAME)

    store.create(DATASET_NAME)
    print(f"Created dataset '{DATASET_NAME}'")

    for eval_input, expected_output, notes in ITEMS:
        item = Evaluable(
            eval_input=eval_input,
            expected_output=expected_output,
            eval_metadata={"notes": notes},
        )
        store.append(DATASET_NAME, item)
        print(f"  Added: {eval_input['question']!r}")

    ds = store.get(DATASET_NAME)
    print(f"\nDataset '{DATASET_NAME}' ready with {len(ds.items)} items.")


if __name__ == "__main__":
    build()
