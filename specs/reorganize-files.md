# re-organize files

The pixie-qa python file organization is becoming messy. Your task is to cleanup the organization.

Here's how the code should be organized (under pixie):

- assets: unchange
- cli: unchanged
- eval: Evaluation related types and functions, mostly from the original evals folder.
  - evaluable.py
  - criteria.py
  - evaluable.py (originally in storage folder)
  - evaluation.py
  - llm_evaluator.py
  - scorers.py
- instrumentation: instrumentation related code
  - llm_tracing.py: everything related to tracing LLM calls. combine the original handler.py, instrumentors.py, observation.py, processor.py, queue.py and spans.py.
  - wrap.py: everything related to wrapping object/provider for injection and/or capturing. combine wrap\*.py
- web: unchanged
