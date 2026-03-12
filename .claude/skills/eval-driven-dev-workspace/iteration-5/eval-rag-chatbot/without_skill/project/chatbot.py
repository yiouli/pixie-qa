"""RAG chatbot — mock version that works without an API key.

This mock returns deterministic answers based on keyword matching.
Suitable for running eval infrastructure without needing ANTHROPIC_API_KEY.
"""

import pixie.instrumentation as px

px.init()


@px.observe()
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


@px.observe()
def answer_question(question: str) -> str:
    """Answer a question using retrieved context.

    (Mock: returns deterministic answers — no LLM API call needed.)
    """
    chunks = retrieve_docs(question)
    # In the real version this calls an LLM; here we return the first chunk directly.
    return chunks[0] if chunks else "I don't have information about that."


def main():
    questions = [
        "What is the capital of France?",
        "What language do people speak in Germany?",
        "What is the population of France?",
        "What currency does Germany use?",
    ]
    for q in questions:
        print(f"Q: {q}")
        print(f"A: {answer_question(q)}")
        print()


if __name__ == "__main__":
    main()
