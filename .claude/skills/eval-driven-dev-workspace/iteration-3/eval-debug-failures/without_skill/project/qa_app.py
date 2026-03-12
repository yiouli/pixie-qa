"""Q&A app instrumented with pixie — has some eval tests that are currently failing."""

import pixie.instrumentation as px
from pixie import enable_storage
from anthropic import Anthropic


@px.observe(name="answer_question")
def answer_question(question: str, context: str = "") -> str:
    """Answer a question, optionally with context."""
    client = Anthropic()
    messages = [{"role": "user", "content": question}]
    if context:
        messages = [{"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=messages,
    )
    return response.content[0].text


def main(question: str, context: str = "") -> str:
    enable_storage()
    return answer_question(question=question, context=context)
