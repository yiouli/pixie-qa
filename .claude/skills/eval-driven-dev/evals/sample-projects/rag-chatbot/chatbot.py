"""Simple RAG chatbot that answers questions using retrieved doc chunks."""

from anthropic import Anthropic


def retrieve_docs(query: str) -> list[str]:
    """Retrieve relevant document chunks for a query (stubbed)."""
    # In production this would call a vector database
    docs = {
        "capital": ["Paris is the capital of France.", "Berlin is the capital of Germany."],
        "population": ["France has a population of about 68 million.", "Germany has about 84 million people."],
        "language": ["French is spoken in France.", "German is spoken in Germany and Austria."],
    }
    for keyword, chunks in docs.items():
        if keyword in query.lower():
            return chunks
    return ["No relevant documents found."]


def answer_question(question: str) -> str:
    """Answer a question using retrieved context and Claude."""
    context_chunks = retrieve_docs(question)
    context = "\n".join(context_chunks)

    client = Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system="You are a helpful assistant. Answer questions based only on the provided context.",
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            }
        ],
    )
    return response.content[0].text


def main():
    questions = [
        "What is the capital of France?",
        "What language do people speak in Germany?",
        "What is the population of France?",
    ]
    for q in questions:
        print(f"Q: {q}")
        print(f"A: {answer_question(q)}")
        print()


if __name__ == "__main__":
    main()
