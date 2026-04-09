Module pixie.cli
================
pixie.cli — command-line interface for pixie.

Provides the ``pixie`` entry point with the following subcommands:

- ``pixie test``    — run eval tests on dataset files.
- ``pixie analyze`` — generate LLM-powered analysis for a test run.
- ``pixie init``    — scaffold the pixie_qa working directory.
- ``pixie start``   — launch the web UI for browsing artifacts.
- ``pixie trace``   — run a Runnable and capture trace output to JSONL.
- ``pixie format``  — convert a trace log into a dataset entry.

Sub-modules
-----------
* pixie.cli.analyze_command
* pixie.cli.format_command
* pixie.cli.init_command
* pixie.cli.main
* pixie.cli.start_command
* pixie.cli.stop_command
* pixie.cli.test_command
* pixie.cli.trace_command