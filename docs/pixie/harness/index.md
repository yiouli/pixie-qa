Module pixie.harness
====================
pixie.harness — test execution harness for dataset-driven evaluation.

Provides:
    - :class:`Runnable` — protocol for structured runnables with lifecycle hooks.
    - :mod:`runner` — dataset loading, validation, evaluator resolution, and
      concurrent entry execution.
    - :mod:`run_result` — test result data models and persistence.

Sub-modules
-----------
* pixie.harness.run_result
* pixie.harness.runnable
* pixie.harness.runner
* pixie.harness.trace_capture