"""Build the email-extraction eval dataset programmatically using the pixie Python API.

Run this script once to populate pixie_datasets/email-extraction.json with
labelled examples. The test file (tests/test_email_extraction.py) then loads
this dataset at eval time — no manual labelling needed.

Usage:
    python build_dataset.py
"""

import os
import sys

# Make sure the local pixie package (repo root) is importable when running
# directly from the project directory.
PIXIE_ROOT = os.environ.get("PIXIE_ROOT", "/home/yiouli/repo/pixie-qa")
if PIXIE_ROOT not in sys.path:
    sys.path.insert(0, PIXIE_ROOT)

from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

DATASET_NAME = "email-extraction"
DATASET_DIR = os.path.join(os.path.dirname(__file__), "pixie_datasets")

# ---------------------------------------------------------------------------
# Dataset items — each has:
#   eval_input:      dict matching the @observe kwargs  →  {"email_text": str}
#   expected_output: the ideal JSON dict the extractor should return
# ---------------------------------------------------------------------------

ITEMS = [
    # --- Billing ---
    Evaluable(
        eval_input={
            "email_text": (
                "Hi, my subscription was charged twice this month. "
                "Please refund the duplicate charge ASAP."
            )
        },
        expected_output={
            "category": "billing",
            "priority": "high",
            "summary": "Customer was charged twice and is requesting an immediate refund.",
        },
    ),
    # --- Technical (high priority / urgent) ---
    Evaluable(
        eval_input={
            "email_text": (
                "The app keeps crashing when I try to upload files larger than 10MB. "
                "This is urgent — I need it for a client presentation tomorrow."
            )
        },
        expected_output={
            "category": "technical",
            "priority": "high",
            "summary": "App crashes on file uploads over 10 MB; customer needs it fixed urgently.",
        },
    ),
    # --- Account (low priority) ---
    Evaluable(
        eval_input={
            "email_text": (
                "Can you tell me how to reset my password? "
                "I can't find the option in settings."
            )
        },
        expected_output={
            "category": "account",
            "priority": "low",
            "summary": "Customer cannot locate the password-reset option in account settings.",
        },
    ),
    # --- General inquiry ---
    Evaluable(
        eval_input={
            "email_text": (
                "Hello, I was wondering whether you offer educational discounts "
                "for university students."
            )
        },
        expected_output={
            "category": "general",
            "priority": "low",
            "summary": "Customer is asking whether educational discounts are available for students.",
        },
    ),
    # --- Technical (medium priority) ---
    Evaluable(
        eval_input={
            "email_text": (
                "The dark mode on your iOS app isn't working correctly — "
                "some text is invisible on dark backgrounds. Not blocking, but annoying."
            )
        },
        expected_output={
            "category": "technical",
            "priority": "medium",
            "summary": "Dark mode on iOS renders some text invisible on dark backgrounds.",
        },
    ),
    # --- Billing (medium priority) ---
    Evaluable(
        eval_input={
            "email_text": (
                "I cancelled my subscription last week but I see it's still listed "
                "as active in my account. Can you confirm the cancellation?"
            )
        },
        expected_output={
            "category": "billing",
            "priority": "medium",
            "summary": "Customer cancelled their subscription but it still appears active.",
        },
    ),
]

# ---------------------------------------------------------------------------
# Build / recreate dataset
# ---------------------------------------------------------------------------


def main() -> None:
    store = DatasetStore(dataset_dir=DATASET_DIR)

    # Delete existing dataset so we can recreate cleanly (idempotent).
    existing = store.list()
    if DATASET_NAME in existing:
        store.delete(DATASET_NAME)
        print(f"Deleted existing dataset '{DATASET_NAME}'.")

    ds = store.create(DATASET_NAME, items=ITEMS)
    print(f"Created dataset '{ds.name}' with {len(ds.items)} items in {DATASET_DIR}/")
    for i, item in enumerate(ds.items):
        preview = str(item.eval_input)[:60]
        print(f"  [{i}] {preview}...")


if __name__ == "__main__":
    main()
