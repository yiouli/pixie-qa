"""Build the golden dataset for the RAG chatbot eval.

Run with:
    PYTHONPATH=/home/yiouli/repo/pixie-qa python build_dataset.py
"""

from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

DATASET_NAME = "rag-chatbot-golden"

golden_items = [
    {
        "eval_input": {"question": "What is the capital of France?"},
        "eval_output": "Paris is the capital of France.",
        "expected_output": "Paris",
    },
    {
        "eval_input": {"question": "What language do people speak in Germany?"},
        "eval_output": "German is spoken in Germany and Austria.",
        "expected_output": "German",
    },
    {
        "eval_input": {"question": "What is the population of France?"},
        "eval_output": "France has a population of about 68 million.",
        "expected_output": "France has a population of about 68 million.",
    },
    {
        "eval_input": {"question": "What currency does Germany use?"},
        "eval_output": "Germany also uses the Euro (EUR).",
        "expected_output": "Euro (EUR)",
    },
]


def build():
    store = DatasetStore()

    # Delete existing dataset if present so we start fresh
    existing = store.list()
    if DATASET_NAME in existing:
        store.delete(DATASET_NAME)
        print(f"Deleted existing dataset '{DATASET_NAME}'.")

    store.create(DATASET_NAME)
    print(f"Created dataset '{DATASET_NAME}'.")

    for item in golden_items:
        store.append(
            DATASET_NAME,
            Evaluable(
                eval_input=item["eval_input"],
                eval_output=item["eval_output"],
                expected_output=item["expected_output"],
            ),
        )
        print(f"  Added: {item['eval_input']['question']!r}")

    print(f"\nDataset '{DATASET_NAME}' built with {len(golden_items)} items.")


if __name__ == "__main__":
    build()
