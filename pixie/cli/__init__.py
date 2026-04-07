"""pixie.cli — command-line interface for pixie.

Provides the ``pixie`` entry point with the following subcommands:

- ``pixie test``    — run eval tests on dataset files.
- ``pixie analyze`` — generate LLM-powered analysis for a test run.
- ``pixie init``    — scaffold the pixie_qa working directory.
- ``pixie start``   — launch the web UI for browsing artifacts.
- ``pixie trace``   — run a Runnable and capture trace output to JSONL.
- ``pixie format``  — convert a trace log into a dataset entry.
"""
