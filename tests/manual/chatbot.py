"""CLI chatbot with tool calling — manual test fixture for wrap() API.

This module implements a simple deterministic chatbot that:
- Receives a user message (purpose="entry")
- Looks up customer profile from a fake database (purpose="input", callable)
- Looks up FAQ answers from a fake knowledge base (purpose="input", value)
- Decides a routing strategy (purpose="state")
- Produces a response (purpose="output")

No LLM calls — all responses are deterministic for reproducible testing.
The entry point ``chat()`` is used as the runnable for evaluation.
"""

from __future__ import annotations

from typing import Any

import pixie

# ── Fake databases ──────────────────────────────────────────────────────────

_CUSTOMER_DB: dict[str, dict[str, Any]] = {
    "C001": {
        "id": "C001",
        "name": "Alice Johnson",
        "tier": "premium",
        "email": "alice@example.com",
    },
    "C002": {
        "id": "C002",
        "name": "Bob Smith",
        "tier": "basic",
        "email": "bob@example.com",
    },
}

_FAQ_KB: dict[str, str] = {
    "business hours": "We are open Monday to Friday, 9am to 5pm.",
    "return policy": "Items can be returned within 30 days of purchase.",
    "shipping": "Standard shipping takes 3-5 business days.",
    "contact": "You can reach us at support@example.com or call 1-800-EXAMPLE.",
}


def _lookup_customer(customer_id: str) -> dict[str, Any]:
    """Fetch a customer profile from the fake database."""
    return _CUSTOMER_DB.get(customer_id, {"id": customer_id, "name": "Unknown", "tier": "basic"})


def _search_faq(query: str) -> str:
    """Search the FAQ knowledge base."""
    query_lower = query.lower()
    for topic, answer in _FAQ_KB.items():
        if topic in query_lower:
            return answer
    return "I don't have specific information about that topic."


# ── Routing logic ───────────────────────────────────────────────────────────


def _determine_route(message: str, customer_tier: str) -> str:
    """Decide how to route the request."""
    msg_lower = message.lower()
    if any(word in msg_lower for word in ("refund", "complaint", "escalate")):
        return "escalation"
    if customer_tier == "premium":
        return "priority"
    return "standard"


# ── Main chatbot entry point ────────────────────────────────────────────────


def chat(entry_input: dict[str, Any] | None) -> None:
    """Process a customer chat message.

    This is the runnable entry point for ``pixie test``.  It uses
    ``pixie.wrap()`` at every stage of processing.

    Args:
        entry_input: Dict with ``user_message`` and optional ``customer_id``.
    """
    if entry_input is None:
        entry_input = {}

    # ── 1. Observe entry-point input (purpose="entry", value) ────────────
    user_message: str = pixie.wrap(
        entry_input.get("user_message", ""),
        purpose="entry",
        name="user_message",
        description="The customer's chat message",
    )
    customer_id: str = pixie.wrap(
        entry_input.get("customer_id", "C001"),
        purpose="entry",
        name="customer_id",
        description="The customer ID from the session",
    )

    # ── 2. Look up customer profile (purpose="input", callable) ──────────
    profile: dict[str, Any] = pixie.wrap(
        lambda: _lookup_customer(customer_id),
        purpose="input",
        name="customer_profile",
        description="Customer profile fetched from the database",
    )()

    # ── 3. Search FAQ knowledge base (purpose="input", value) ────────────
    faq_answer: str = pixie.wrap(
        _search_faq(user_message),
        purpose="input",
        name="faq_result",
        description="FAQ search result for the user's query",
    )

    # ── 4. Determine routing (purpose="state") ──────────────────────────
    route: str = pixie.wrap(
        _determine_route(user_message, profile.get("tier", "basic")),
        purpose="state",
        name="routing_decision",
        description="How the request is routed (standard/priority/escalation)",
    )

    # ── 5. Generate response (purpose="output", value) ──────────────────
    greeting = f"Hello {profile.get('name', 'customer')}!"
    if route == "escalation":
        response = f"{greeting} I understand your concern. Let me connect you with a specialist."
    elif route == "priority":
        response = f"{greeting} As a valued premium member, here's your answer: {faq_answer}"
    else:
        response = f"{greeting} {faq_answer}"

    pixie.wrap(
        response,
        purpose="output",
        name="chat_response",
        description="The chatbot's response to the customer",
    )

    # ── 6. Log a callable-based output (purpose="output", callable) ─────
    def _build_summary() -> dict[str, Any]:
        return {
            "customer_id": customer_id,
            "customer_name": profile.get("name"),
            "route": route,
            "response_length": len(response),
        }

    pixie.wrap(
        _build_summary,
        purpose="output",
        name="interaction_summary",
        description="Summary of the chat interaction",
    )()
