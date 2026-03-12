"""RAG chatbot — mock version instrumented with pixie for tracing.

This version wraps the core functions with pixie's @observe decorator
and enable_storage() so all spans are persisted to SQLite.
"""

import os
import sys

# Ensure pixie is importable
sys.path.insert(0, os.environ.get("PIXIE_PATH", "/home/yiouli/repo/pixie-qa"))

from pixie import enable_storage
from pixie.instrumentation import observe, flush


# --------------------------------------------------------------------------
# Instrumented application functions
# --------------------------------------------------------------------------


@observe()
def retrieve_docs(query: str) -> list[str]:
    """Retrieve relevant document chunks for a query."""
    docs = {
        "capital": ["Paris is the capital of France.", "Berlin is the capital of Germany."],
        "population": ["France has a population of about 68 million.", "Germany has about 84 million people."],
        "language": ["French is spoken in France.", "German is spoken in Germany and Austria."],
        "currency": ["France uses the Euro (EUR).", "Germany also uses the Euro (EUR)."],
    }
    for keyword, chunks in docs.items():
        if keyword in query.lower():
            return chunks
    return ["No relevant documents found."]


@observe()
def answer_question(question: str) -> str:
    """Answer a question using retrieved context.

    (Mock: returns deterministic answers — no LLM API call needed.)
    """
    chunks = retrieve_docs(question)
    return chunks[0] if chunks else "I don't have information about that."


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------


def main() -> None:
    enable_storage()

    questions = [
        "What is the capital of France?",
        "What language do people speak in Germany?",
        "What is the population of France?",
        "What currency does Germany use?",
    ]
    for q in questions:
        answer = answer_question(q)
        print(f"Q: {q}")
        print(f"A: {answer}")
        print()

    flush()
    print("Traces saved to pixie_observations.db")


if __name__ == "__main__":
    main()
