"""Build the golden dataset for the email classifier eval.

Run this script once to create the dataset file:

    PYTHONPATH=/home/yiouli/repo/pixie-qa python build_dataset.py

The dataset is saved to ./datasets/email-classifier-golden.json.
Each item contains:
  - eval_input:      the raw email text (passed to extract_from_email)
  - expected_output: the expected dict with category, priority, and summary
"""

from __future__ import annotations

import json
from pathlib import Path

from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

DATASET_NAME = "email-classifier-golden"
DATASET_DIR = Path(__file__).parent / "datasets"

# ---------------------------------------------------------------------------
# Golden examples — (email_text, expected_output)
# ---------------------------------------------------------------------------

GOLDEN_EXAMPLES: list[tuple[str, dict]] = [
    # --- billing ---
    (
        "Hi, my subscription was charged twice this month. Please refund the duplicate charge ASAP.",
        {
            "category": "billing",
            "priority": "high",
            "summary": "Hi, my subscription was charged twice this month",
        },
    ),
    (
        "I received an invoice for $99 but I cancelled my subscription last month.",
        {
            "category": "billing",
            "priority": "low",
            "summary": "I received an invoice for $99 but I cancelled my subscription last month",
        },
    ),
    (
        "The payment failed three times and I can't complete my purchase. Please fix this soon.",
        {
            "category": "billing",
            "priority": "medium",
            "summary": "The payment failed three times and I can't complete my purchase",
        },
    ),
    # --- technical ---
    (
        "The app keeps crashing when I try to upload files larger than 10MB. This is urgent.",
        {
            "category": "technical",
            "priority": "high",
            "summary": "The app keeps crashing when I try to upload files larger than 10MB",
        },
    ),
    (
        "There is a bug where the download button does nothing when I click it.",
        {
            "category": "technical",
            "priority": "low",
            "summary": "There is a bug where the download button does nothing when I click it",
        },
    ),
    (
        "I keep getting an error message every time I open the dashboard. Very frustrating.",
        {
            "category": "technical",
            "priority": "medium",
            "summary": "I keep getting an error message every time I open the dashboard",
        },
    ),
    # --- account ---
    (
        "Can you tell me how to reset my password? I can't find the option in settings.",
        {
            "category": "account",
            "priority": "low",
            "summary": "Can you tell me how to reset my password",
        },
    ),
    (
        "I can't login to my account. The username and password I set are not being accepted.",
        {
            "category": "account",
            "priority": "low",
            "summary": "I can't login to my account",
        },
    ),
    (
        "My account was locked out immediately after I tried to sign in. Please fix this ASAP.",
        {
            "category": "account",
            "priority": "high",
            "summary": "My account was locked out immediately after I tried to sign in",
        },
    ),
    # --- general ---
    (
        "Just wondering when your mobile app will support dark mode.",
        {
            "category": "general",
            "priority": "low",
            "summary": "Just wondering when your mobile app will support dark mode",
        },
    ),
    (
        "I love your product! Any chance you will add keyboard shortcuts soon?",
        {
            "category": "general",
            "priority": "medium",
            "summary": "I love your product! Any chance you will add keyboard shortcuts soon",
        },
    ),
    (
        "Do you have any documentation on how to use the API?",
        {
            "category": "general",
            "priority": "low",
            "summary": "Do you have any documentation on how to use the API",
        },
    ),
]


def build() -> None:
    store = DatasetStore(dataset_dir=DATASET_DIR)

    # Remove existing dataset if present (allows re-running this script)
    try:
        store.delete(DATASET_NAME)
        print(f"Deleted existing dataset '{DATASET_NAME}'")
    except FileNotFoundError:
        pass

    items = [
        Evaluable(
            eval_input=email_text,
            expected_output=expected,
        )
        for email_text, expected in GOLDEN_EXAMPLES
    ]

    dataset = store.create(DATASET_NAME, items=items)
    print(f"Created dataset '{DATASET_NAME}' with {len(dataset.items)} items")
    print(f"Saved to: {DATASET_DIR / (DATASET_NAME.replace(' ', '-') + '.json')}")


if __name__ == "__main__":
    build()
