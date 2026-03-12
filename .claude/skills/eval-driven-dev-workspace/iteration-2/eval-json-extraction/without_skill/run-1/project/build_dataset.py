"""Build the email-classifier golden dataset for eval-based testing.

Run this script once to create (or recreate) the dataset:

    python build_dataset.py

The dataset is written to ./pixie_datasets/ as a JSON file and can then be
consumed by test_extractor.py via assert_dataset_pass().
"""

import json
import sys

sys.path.insert(0, "/home/yiouli/repo/pixie-qa")

from pixie.dataset import DatasetStore
from pixie.storage.evaluable import Evaluable

# ---------------------------------------------------------------------------
# Golden test cases
# Each item holds the raw email text as eval_input and the expected
# structured extraction as expected_output (a JSON dict serialised to str).
# ---------------------------------------------------------------------------

DATASET_NAME = "email-classifier-golden"

ITEMS = [
    Evaluable(
        eval_input=(
            "Hi, my subscription was charged twice this month. "
            "Please refund the duplicate charge ASAP."
        ),
        expected_output=json.dumps(
            {
                "category": "billing",
                "priority": "high",
                "summary": "Customer was charged twice and is requesting an urgent refund.",
            }
        ),
    ),
    Evaluable(
        eval_input=(
            "The app keeps crashing when I try to upload files larger than 10MB. "
            "This is urgent."
        ),
        expected_output=json.dumps(
            {
                "category": "technical",
                "priority": "high",
                "summary": "App crashes on file uploads larger than 10 MB.",
            }
        ),
    ),
    Evaluable(
        eval_input=(
            "Can you tell me how to reset my password? "
            "I can't find the option in settings."
        ),
        expected_output=json.dumps(
            {
                "category": "account",
                "priority": "medium",
                "summary": "User cannot locate the password reset option in settings.",
            }
        ),
    ),
    Evaluable(
        eval_input=(
            "I'd love to know if you offer any discounts for non-profit organisations."
        ),
        expected_output=json.dumps(
            {
                "category": "general",
                "priority": "low",
                "summary": "User is enquiring about potential discounts for non-profit organisations.",
            }
        ),
    ),
    Evaluable(
        eval_input=(
            "My account has been locked after too many failed login attempts. "
            "I need access restored immediately as I have a deadline in one hour."
        ),
        expected_output=json.dumps(
            {
                "category": "account",
                "priority": "high",
                "summary": "Account locked due to failed logins; user needs immediate access for an urgent deadline.",
            }
        ),
    ),
]


def main() -> None:
    store = DatasetStore()

    # Remove a stale copy if it already exists so the script is idempotent.
    if DATASET_NAME in store.list():
        store.delete(DATASET_NAME)

    ds = store.create(DATASET_NAME, items=ITEMS)
    print(f"Created dataset '{DATASET_NAME}' with {len(ds.items)} items.")
    print(f"Stored in: {store._dir}")  # noqa: SLF001


if __name__ == "__main__":
    main()
