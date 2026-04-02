# Run Harness Example: Standalone Function (No Infrastructure)

**When your app is a single function or module** with no server, no database, no external services.

**Approach**: Import the function directly and call it. This is the simplest case.

```python
# pixie_qa/scripts/run_app.py
from pixie import enable_storage, observe

# Enable trace capture
enable_storage()

from myapp.agent import answer_question

@observe
def run_agent(question: str) -> str:
    """Wrapper that captures traces for the agent call."""
    return answer_question(question)

def main() -> None:
    inputs = [
        "What are your business hours?",
        "How do I reset my password?",
        "Tell me about your return policy",
    ]
    for q in inputs:
        result = run_agent(q)
        print(f"Q: {q}")
        print(f"A: {result}")
        print("---")

if __name__ == "__main__":
    main()
```

If the function depends on something that needs mocking (e.g., a vector store client), patch it before calling:

```python
from unittest.mock import MagicMock
import myapp.retriever as retriever

# Mock the vector store with a simple keyword search
retriever.vector_client = MagicMock()
retriever.vector_client.search.return_value = [
    {"text": "Business hours: Mon-Fri 9am-5pm", "score": 0.95}
]
```

**Run**: `uv run python -m pixie_qa.scripts.run_app`
