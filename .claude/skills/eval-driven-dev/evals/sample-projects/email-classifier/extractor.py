"""Extract structured information from customer support emails using GPT-4."""

import json

from openai import OpenAI

SYSTEM_PROMPT = """You are a support ticket classifier. Given a customer support email,
extract the following fields as JSON:
- category: one of "billing", "technical", "account", "general"
- priority: one of "low", "medium", "high"
- summary: a single sentence summarizing the issue

Respond with valid JSON only, no extra text."""


def extract_from_email(email_text: str) -> dict:
    """Extract structured fields from a customer support email."""
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": email_text},
        ],
        temperature=0,
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


# ---- ad-hoc testing (replace with proper eval tests) ----
if __name__ == "__main__":
    sample_emails = [
        "Hi, my subscription was charged twice this month. Please refund the duplicate charge ASAP.",
        "The app keeps crashing when I try to upload files larger than 10MB. This is urgent.",
        "Can you tell me how to reset my password? I can't find the option in settings.",
    ]
    for email in sample_emails:
        result = extract_from_email(email)
        print(result)
