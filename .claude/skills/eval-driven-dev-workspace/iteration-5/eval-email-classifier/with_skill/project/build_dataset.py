"""Build the golden dataset for the email classifier eval."""

import sys
import os

sys.path.insert(0, "/home/yiouli/repo/pixie-qa")

# Set dataset dir relative to project
os.environ.setdefault(
    "PIXIE_DATASET_DIR",
    os.path.join(os.path.dirname(__file__), "pixie_datasets"),
)

from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

DATASET_NAME = "email-classifier-golden"

# Golden items: (email_text, expected_output)
GOLDEN_ITEMS = [
    (
        "Hi, my subscription was charged twice this month. Please refund the duplicate charge ASAP.",
        {
            "category": "billing",
            "priority": "high",
            "summary": "Hi, my subscription was charged twice this month",
        },
    ),
    (
        "The app keeps crashing when I try to upload files larger than 10MB. This is urgent.",
        {
            "category": "technical",
            "priority": "high",
            "summary": "The app keeps crashing when I try to upload files larger than 10MB",
        },
    ),
    (
        "Can you tell me how to reset my password? I can't find the option in settings.",
        {
            "category": "account",
            "priority": "low",
            "summary": "Can you tell me how to reset my password? I can't find the option in settings",
        },
    ),
    (
        "Just wondering when your mobile app will support dark mode.",
        {
            "category": "general",
            "priority": "low",
            "summary": "Just wondering when your mobile app will support dark mode",
        },
    ),
    (
        "I have a question about my billing plan. When does my subscription renew?",
        {
            "category": "billing",
            "priority": "low",
            "summary": "I have a question about my billing plan",
        },
    ),
    (
        "There is a bug in the export feature that is really frustrating. Could you fix it soon?",
        {
            "category": "technical",
            "priority": "medium",
            "summary": "There is a bug in the export feature that is really frustrating",
        },
    ),
]

store = DatasetStore()

# Delete existing dataset if present to start fresh
existing = store.list()
if DATASET_NAME in existing:
    store.delete(DATASET_NAME)

store.create(DATASET_NAME)

for email_text, expected in GOLDEN_ITEMS:
    store.append(
        DATASET_NAME,
        Evaluable(
            eval_input={"email_text": email_text},
            eval_output=None,
            expected_output=expected,
        ),
    )

ds = store.get(DATASET_NAME)
print(f"Created dataset '{DATASET_NAME}' with {len(ds.items)} items.")
for i, item in enumerate(ds.items):
    print(f"  [{i}] {item.eval_input['email_text'][:60]!r}... → expected: {item.expected_output}")
