"""Build the email-classifier-golden dataset using the pixie Python API.

Run with:
  cd /home/yiouli/repo/pixie-qa/.claude/skills/eval-driven-dev-workspace/iteration-3/eval-email-classifier/with_skill/project
  PYTHONPATH=/home/yiouli/repo/pixie-qa python build_dataset.py
"""

import sys
sys.path.insert(0, '/home/yiouli/repo/pixie-qa')

from pixie import enable_storage
import pixie.instrumentation as px
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable

# Must call enable_storage so traces are captured
enable_storage()

# Import the instrumented function
from extractor import extract_from_email

DATASET_NAME = "email-classifier-golden"

# Sample emails covering normal cases and edge cases
SAMPLE_EMAILS = [
    {
        "email_text": "Hi, my subscription was charged twice this month. Please refund the duplicate charge ASAP.",
        "notes": "billing high-priority duplicate charge",
    },
    {
        "email_text": "The app keeps crashing when I try to upload files larger than 10MB. This is urgent.",
        "notes": "technical high-priority crash on upload",
    },
    {
        "email_text": "Can you tell me how to reset my password? I can't find the option in settings.",
        "notes": "account low-priority password reset",
    },
    {
        "email_text": "Just wondering when your mobile app will support dark mode.",
        "notes": "general low-priority feature request",
    },
    {
        "email_text": "I received an invoice for services I never signed up for. Please investigate immediately.",
        "notes": "billing high-priority invoice dispute",
    },
    {
        "email_text": "Getting a login error every time I try to sign in from my laptop. It's been frustrating.",
        "notes": "account medium-priority login error",
    },
    {
        "email_text": "",
        "notes": "edge case: empty email",
    },
]

# Create dataset
store = DatasetStore()
try:
    store.create(DATASET_NAME)
    print(f"Created dataset '{DATASET_NAME}'")
except Exception as e:
    print(f"Dataset may already exist: {e}")

# Run extractor on each email and capture output, then add to dataset
for sample in SAMPLE_EMAILS:
    email_text = sample["email_text"]
    notes = sample["notes"]

    # Run the observed function to produce a trace
    output = extract_from_email(email_text=email_text)
    print(f"  [{notes}] -> {output}")

    # Add to dataset using Python API
    store.append(
        DATASET_NAME,
        Evaluable(
            eval_input={"email_text": email_text},
            eval_output=output,
            eval_metadata={"notes": notes},
        ),
    )

px.flush()

# Verify
ds = store.get(DATASET_NAME)
print(f"\nDataset '{DATASET_NAME}' now has {len(ds.items)} items.")
for i, item in enumerate(ds.items):
    print(f"  [{i}] input_len={len(item.eval_input.get('email_text', ''))} "
          f"output_keys={list(item.eval_output.keys()) if isinstance(item.eval_output, dict) else '?'} "
          f"notes={item.eval_metadata.get('notes', '')}")
