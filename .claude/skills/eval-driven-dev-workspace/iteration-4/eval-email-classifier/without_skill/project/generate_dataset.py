"""Run the instrumented email classifier on sample inputs and save traces as a dataset.

Usage:
    PYTHONPATH=/home/yiouli/repo/pixie-qa python generate_dataset.py

Outputs:
    pixie_datasets/email-classifier-traces.json  — dataset of ObserveSpan evaluables
"""

import json
import sys
import os

# Allow running from the project directory
sys.path.insert(0, os.path.dirname(__file__))

import pixie.instrumentation as px
from pixie.evals.trace_capture import capture_traces
from pixie.storage.evaluable import as_evaluable
from pixie.storage.tree import build_tree
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

from instrumented_extractor import extract_from_email

SAMPLE_EMAILS = [
    "Hi, my subscription was charged twice this month. Please refund the duplicate charge ASAP.",
    "The app keeps crashing when I try to upload files larger than 10MB. This is urgent.",
    "Can you tell me how to reset my password? I can't find the option in settings.",
    "Just wondering when your mobile app will support dark mode.",
    "I received an invoice for an amount I don't recognize. Please help clarify this billing issue.",
    "The download button is broken — clicking it does nothing. This bug has been around for weeks.",
    "I need to update my account username. How do I do that?",
    "Great product overall! When will you add support for custom themes?",
    "My payment failed three times now. This is frustrating. Can you fix this soon?",
    "I can't sign in anymore after resetting my password. It says 'invalid credentials'.",
]

DATASET_NAME = "email-classifier-traces"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(PROJECT_DIR, "pixie_datasets")


def main() -> None:
    store = DatasetStore(dataset_dir=DATASET_DIR)

    # Remove existing dataset so we can recreate it cleanly
    try:
        store.delete(DATASET_NAME)
        print(f"Deleted existing dataset '{DATASET_NAME}'.")
    except FileNotFoundError:
        pass

    evaluables: list[Evaluable] = []

    for email in SAMPLE_EMAILS:
        with capture_traces() as handler:
            result = extract_from_email(email)

        if not handler.spans:
            print(f"WARNING: no spans captured for email: {email[:50]!r}")
            continue

        tree = build_tree(handler.spans)
        root_span = tree[0].span
        ev = as_evaluable(root_span)
        evaluables.append(ev)

        print(f"Captured: {json.dumps(result)}")

    dataset = store.create(DATASET_NAME, items=evaluables)
    print(f"\nDataset '{dataset.name}' saved to {DATASET_DIR}")
    print(f"  Items: {len(dataset.items)}")


if __name__ == "__main__":
    main()
