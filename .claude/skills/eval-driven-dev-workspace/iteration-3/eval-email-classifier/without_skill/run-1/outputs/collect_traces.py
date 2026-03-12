"""Collect traces from the email classifier and save them as a dataset.

Instruments extractor.py, runs it on sample emails, and stores the
resulting ObserveSpan traces as a pixie dataset JSON file.

Usage:
    PYTHONPATH=/home/yiouli/repo/pixie-qa python collect_traces.py
"""

import json
import os
import sys

# Ensure the project directory is on the path so extractor imports work.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

import pixie.instrumentation as px
from pixie.evals.trace_capture import capture_traces
from pixie.dataset.store import DatasetStore
from pixie.storage.evaluable import Evaluable
from extractor import extract_from_email

# Wrap the extractor function with the @observe decorator so pixie
# captures its inputs and outputs automatically.
observed_extract = px.observe(name="extract_from_email")(extract_from_email)

SAMPLE_EMAILS = [
    "Hi, my subscription was charged twice this month. Please refund the duplicate charge ASAP.",
    "The app keeps crashing when I try to upload files larger than 10MB. This is urgent.",
    "Can you tell me how to reset my password? I can't find the option in settings.",
    "Just wondering when your mobile app will support dark mode.",
    "I received an invoice for $99 but my plan is only $49. Please fix this billing error.",
    "The download button is broken on the export page. I keep getting a 404 error.",
    "I forgot my username and I can't sign in. How do I recover my account?",
    "Great product overall, just a general question about upcoming features.",
]

DATASET_NAME = "email-classifier-traces"
DATASET_DIR = os.path.join(PROJECT_DIR, "pixie_datasets")


def main() -> None:
    evaluables: list[Evaluable] = []

    with capture_traces() as handler:
        for email in SAMPLE_EMAILS:
            result = observed_extract(email)
            print(f"Input : {email[:60]!r}...")
            print(f"Output: {json.dumps(result)}")
            print()

    # Each call produces one ObserveSpan.
    print(f"Captured {len(handler.spans)} spans.")

    for span in handler.spans:
        # span.input is the serialized function arguments (JSON string or dict)
        # span.output is the serialized return value
        evaluable = Evaluable(
            eval_input=span.input,
            eval_output=span.output,
        )
        evaluables.append(evaluable)

    store = DatasetStore(dataset_dir=DATASET_DIR)

    # Remove existing dataset so the script is re-runnable.
    try:
        store.delete(DATASET_NAME)
        print(f"Deleted existing dataset '{DATASET_NAME}'.")
    except FileNotFoundError:
        pass

    dataset = store.create(DATASET_NAME, items=evaluables)
    print(f"Saved dataset '{dataset.name}' with {len(dataset.items)} items.")
    print(f"Dataset file: {os.path.join(DATASET_DIR, 'email-classifier-traces.json')}")


if __name__ == "__main__":
    main()
