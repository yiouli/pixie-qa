"""Email classifier — mock version that works without an API key.

This mock classifies emails using simple keyword rules.
Suitable for running eval infrastructure without needing OPENAI_API_KEY.
"""

import json

from pixie.instrumentation import init, observe

init()


@observe()
def extract_from_email(email_text: str) -> dict:
    """Extract structured info from a customer support email.

    Returns a dict with:
      - category: "billing" | "technical" | "account" | "general"
      - priority: "low" | "medium" | "high"
      - summary: one-sentence summary

    (Mock: uses keyword rules — no LLM API call needed.)
    """
    text = email_text.lower()

    # Determine category
    if any(w in text for w in ["charge", "refund", "invoice", "payment", "billing", "subscription"]):
        category = "billing"
    elif any(w in text for w in ["crash", "error", "bug", "broken", "not working", "upload", "download"]):
        category = "technical"
    elif any(w in text for w in ["password", "login", "account", "username", "sign in", "reset"]):
        category = "account"
    else:
        category = "general"

    # Determine priority
    if any(w in text for w in ["urgent", "asap", "immediately", "critical", "crashing", "duplicate charge"]):
        priority = "high"
    elif any(w in text for w in ["soon", "when possible", "annoying", "frustrating"]):
        priority = "medium"
    else:
        priority = "low"

    # Generate summary
    first_sentence = email_text.strip().split(".")[0].strip()
    summary = first_sentence[:100] if first_sentence else "Customer support request."

    return {"category": category, "priority": priority, "summary": summary}


if __name__ == "__main__":
    sample_emails = [
        "Hi, my subscription was charged twice this month. Please refund the duplicate charge ASAP.",
        "The app keeps crashing when I try to upload files larger than 10MB. This is urgent.",
        "Can you tell me how to reset my password? I can't find the option in settings.",
        "Just wondering when your mobile app will support dark mode.",
    ]
    for email in sample_emails:
        result = extract_from_email(email)
        print(json.dumps(result, indent=2))
        print()
