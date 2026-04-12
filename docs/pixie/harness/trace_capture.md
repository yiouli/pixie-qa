Module pixie.harness.trace_capture
==================================
Per-entry unified trace capture for ``pixie test``.

Provides :class:`EntryTraceCollector`, which collects **all** events for
each dataset entry — input data, ``wrap()`` emissions (input, output,
state), and ``LLMSpan`` objects — preserving chronological order.

A context variable (:data:`current_entry_index`) identifies which entry
the current async task belongs to, so concurrent entries are tracked
independently.

The companion :class:`EntryTraceLogProcessor` is an OTel
``LogRecordProcessor`` that intercepts ``wrap()`` emissions and routes
them to the active :class:`EntryTraceCollector`.

Usage::

    collector = EntryTraceCollector()
    set_active_collector(collector)
    add_handler(collector)

    log_processor = EntryTraceLogProcessor()
    logger_provider.add_log_record_processor(log_processor)

    current_entry_index.set(0)
    record_input_data(0, {"user_message": "hi"})
    # …run entry… (wrap events and LLM spans are captured automatically)
    count = collector.write_entry_trace(0, "/path/to/traces/entry-0.jsonl")

Variables
---------

`current_entry_index: _contextvars.ContextVar[int | None]`
:   Context variable set by the runner to identify the current dataset entry.

Functions
---------

`def get_active_collector() ‑> pixie.harness.trace_capture.EntryTraceCollector | None`
:   Return the active :class:`EntryTraceCollector`, or ``None``.

`def record_input_data(entry_index: int, kwargs: dict[str, Any]) ‑> None`
:   Store input data in the active collector for later trace writing.
    
    No-op if no collector is active.

`def set_active_collector(collector: EntryTraceCollector | None) ‑> None`
:   Set the module-level active :class:`EntryTraceCollector`.

Classes
-------

`EntryTraceCollector()`
:   Collects input data, wrap events, and LLM spans per entry.
    
    Thread-safe: LLM spans arrive from the OTel delivery thread while
    wrap events arrive from the event loop thread.  The entry index is
    read from :data:`current_entry_index` at the time each event arrives;
    events without an entry context are silently dropped.

    ### Ancestors (in MRO)

    * pixie.instrumentation.llm_tracing.InstrumentationHandler

    ### Methods

    `def add_wrap_event(self, entry_index: int, body: dict[str, Any]) ‑> None`
    :   Add a wrap event for an entry (called by :class:`EntryTraceLogProcessor`).

    `async def on_llm(self, span: LLMSpan) ‑> None`
    :   Accumulate *span* under the current entry index.

    `def set_input_data(self, entry_index: int, kwargs: dict[str, Any]) ‑> None`
    :   Store the runnable input data for an entry.

    `def write_entry_trace(self, entry_index: int, output_path: str) ‑> int`
    :   Write the full trace for *entry_index* to a JSONL file.
        
        The output contains, in chronological order:
        
        1. An ``InputDataLog`` record with the input data.
        2. Interleaved wrap events and LLM span records, sorted by
           timestamp (``captured_at`` for wraps, ``started_at`` for spans).
        
        Creates parent directories if needed.
        
        Args:
            entry_index: The dataset entry index.
            output_path: Absolute path to the JSONL output file.
        
        Returns:
            The total number of records written (including input data).

`TraceCaptureHandler()`
:   Collects input data, wrap events, and LLM spans per entry.
    
    Thread-safe: LLM spans arrive from the OTel delivery thread while
    wrap events arrive from the event loop thread.  The entry index is
    read from :data:`current_entry_index` at the time each event arrives;
    events without an entry context are silently dropped.

    ### Ancestors (in MRO)

    * pixie.instrumentation.llm_tracing.InstrumentationHandler

    ### Methods

    `def add_wrap_event(self, entry_index: int, body: dict[str, Any]) ‑> None`
    :   Add a wrap event for an entry (called by :class:`EntryTraceLogProcessor`).

    `async def on_llm(self, span: LLMSpan) ‑> None`
    :   Accumulate *span* under the current entry index.

    `def set_input_data(self, entry_index: int, kwargs: dict[str, Any]) ‑> None`
    :   Store the runnable input data for an entry.

    `def write_entry_trace(self, entry_index: int, output_path: str) ‑> int`
    :   Write the full trace for *entry_index* to a JSONL file.
        
        The output contains, in chronological order:
        
        1. An ``InputDataLog`` record with the input data.
        2. Interleaved wrap events and LLM span records, sorted by
           timestamp (``captured_at`` for wraps, ``started_at`` for spans).
        
        Creates parent directories if needed.
        
        Args:
            entry_index: The dataset entry index.
            output_path: Absolute path to the JSONL output file.
        
        Returns:
            The total number of records written (including input data).

`EntryTraceLogProcessor()`
:   Route ``wrap()`` emissions to the active :class:`EntryTraceCollector`.
    
    Each wrap event is stamped with ``captured_at`` and filed under the
    current entry index (from :data:`current_entry_index`).  Events
    outside an entry context are silently dropped.

    ### Ancestors (in MRO)

    * opentelemetry.sdk._logs._internal.LogRecordProcessor
    * abc.ABC

    ### Methods

    `def force_flush(self, timeout_millis: int = 30000) ‑> bool`
    :   Export all the received logs to the configured Exporter that have not yet
        been exported.
        
        Args:
            timeout_millis: The maximum amount of time to wait for logs to be
                exported.
        
        Returns:
            False if the timeout is exceeded, True otherwise.

    `def on_emit(self, log_record: ReadWriteLogRecord) ‑> None`
    :   Emits the ``ReadWriteLogRecord``.
        
        Implementers should handle any exceptions raised during log processing
        to prevent application crashes. See the class docstring for details
        on error handling expectations.

    `def shutdown(self) ‑> None`
    :   Called when a :class:`opentelemetry.sdk._logs.Logger` is shutdown