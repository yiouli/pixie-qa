Module pixie.cli.trace_command
==============================
``pixie trace`` CLI command — run a Runnable and capture trace output.

Usage::

    pixie trace --runnable path/to/file.py:MyRunnable \
                --input kwargs.json \
                --output trace.jsonl

Functions
---------

`main(argv: list[str] | None = None) ‑> int`
:   Entry point for ``pixie trace`` command.
    
    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.
    
    Returns:
        Exit code: 0 on success, 1 on error.

Classes
-------

`LLMTraceLogger(trace_log_processor: TraceLogProcessor)`
:   Base class for instrumentation handlers.
    
    Both methods are optional async overrides — a handler only implementing
    on_llm is valid, and vice versa.  Implementations may be long-running
    (e.g. calling external APIs) since each handler coroutine runs
    concurrently with other registered handlers.

    ### Ancestors (in MRO)

    * pixie.instrumentation.llm_tracing.InstrumentationHandler