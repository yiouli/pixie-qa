"""Build a golden-set dataset for the RAG chatbot using pixie DatasetStore."""

from pixie.dataset import DatasetStore
from pixie.storage.evaluable import Evaluable

DATASET_NAME = "rag-chatbot-golden-set"


def build_dataset() -> None:
    store = DatasetStore()

    # Remove any previous version so this script is idempotent
    if DATASET_NAME in store.list():
        store.delete(DATASET_NAME)

    items = [
        Evaluable(
            eval_input="What is the capital of France?",
            expected_output="Paris",
            eval_metadata={"topic": "capital", "country": "France"},
        ),
        Evaluable(
            eval_input="What is the capital of Germany?",
            expected_output="Berlin",
            eval_metadata={"topic": "capital", "country": "Germany"},
        ),
        Evaluable(
            eval_input="What language do people speak in France?",
            expected_output="French",
            eval_metadata={"topic": "language", "country": "France"},
        ),
        Evaluable(
            eval_input="What language do people speak in Germany?",
            expected_output="German",
            eval_metadata={"topic": "language", "country": "Germany"},
        ),
        Evaluable(
            eval_input="What is the population of France?",
            expected_output="about 68 million",
            eval_metadata={"topic": "population", "country": "France"},
        ),
        Evaluable(
            eval_input="How many people live in Germany?",
            expected_output="about 84 million",
            eval_metadata={"topic": "population", "country": "Germany"},
        ),
    ]

    ds = store.create(DATASET_NAME, items=items)
    print(f"Created dataset '{DATASET_NAME}' with {len(ds.items)} items.")
    for item in ds.items:
        print(f"  [{item.eval_input!r}] -> expected: {item.expected_output!r}")


if __name__ == "__main__":
    build_dataset()
