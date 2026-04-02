# Run Harness Example: CLI / Command-Line App

**When your app is invoked from the command line** (e.g., `python -m myapp`, a CLI tool).

**Do NOT call an inner function** like `agent.respond()` directly just because it's simpler. Between the entry point and that inner function, the app does request handling, state management, prompt assembly, routing — all of which is under test. When you call an inner function, you skip all of that and end up reimplementing it in your test. Now your test is testing test code, not app code.

**Approach**: Invoke the app's entry point via `subprocess.run()`, capture stdout/stderr, parse results.

```python
# pixie_qa/scripts/run_app.py
import subprocess
import sys
import json

def run_app(user_input: str) -> str:
    """Run the CLI app with the given input and return its output."""
    result = subprocess.run(
        [sys.executable, "-m", "myapp", "--query", user_input],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"App failed: {result.stderr}")
    return result.stdout.strip()

def main() -> None:
    inputs = [
        "What are your business hours?",
        "How do I reset my password?",
        "Tell me about your return policy",
    ]
    for user_input in inputs:
        output = run_app(user_input)
        print(f"Input: {user_input}")
        print(f"Output: {output}")
        print("---")

if __name__ == "__main__":
    main()
```

If the CLI app needs external dependencies mocked, create a wrapper script that patches them before invoking the entry point:

```python
# pixie_qa/scripts/patched_app.py
"""Entry point that patches DB/cache before running the real app."""
import myapp.config as config
config.redis_url = "mock://localhost"  # or use a mock implementation

from myapp.main import main
main()
```

**Run**: `uv run python -m pixie_qa.scripts.run_app`
