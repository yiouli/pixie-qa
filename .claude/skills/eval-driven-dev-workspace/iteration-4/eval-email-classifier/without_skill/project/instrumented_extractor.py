"""Instrumented email classifier using pixie @observe decorator.

Wraps extract_from_email with pixie instrumentation so every call is
captured as an ObserveSpan (input = email_text, output = extracted dict).
"""

import sys
import os

# Allow running with: PYTHONPATH=/home/yiouli/repo/pixie-qa python instrumented_extractor.py
from pixie.instrumentation import observe
from extractor import extract_from_email as _extract_from_email


@observe(name="extract_from_email")
def extract_from_email(email_text: str) -> dict:
    """Instrumented wrapper around the email extractor.

    Captures the raw email text as input and the classification dict as
    output via pixie's @observe decorator.
    """
    return _extract_from_email(email_text)
