Module pixie.config
===================
Centralized configuration with env var and ``.env`` overrides.

All environment variables are prefixed with ``PIXIE_``. ``get_config()`` loads
the nearest ``.env`` from the current working directory at call time, while
preserving any variables already present in ``os.environ``. Values are still
resolved at call time rather than import time so tests can safely manipulate
the process environment before calling :func:`get_config`.

Variables
---------

`DEFAULT_ROOT`
:   Default root directory for all pixie-generated artefacts.

Functions
---------

`get_config() ‑> pixie.config.PixieConfig`
:   Read configuration from environment variables with defaults.
    
    Supported variables:
        - ``PIXIE_ROOT`` — overrides :attr:`PixieConfig.root` (the base
          directory for all artefacts)
        - ``PIXIE_DATASET_DIR`` — overrides :attr:`PixieConfig.dataset_dir`
        - ``PIXIE_RATE_LIMIT_ENABLED`` — enables evaluator rate limiting
        - ``PIXIE_RATE_LIMIT_RPS`` — overrides :attr:`RateLimitConfig.rps`
        - ``PIXIE_RATE_LIMIT_RPM`` — overrides :attr:`RateLimitConfig.rpm`
        - ``PIXIE_RATE_LIMIT_TPS`` — overrides :attr:`RateLimitConfig.tps`
        - ``PIXIE_RATE_LIMIT_TPM`` — overrides :attr:`RateLimitConfig.tpm`
        - ``PIXIE_TRACE_OUTPUT`` — path for JSONL trace output file;
          overrides :attr:`PixieConfig.trace_output`
        - ``PIXIE_TRACING`` — set to ``1``/``true``/``yes``/``on`` to enable
          tracing mode; overrides :attr:`PixieConfig.tracing_enabled`

Classes
-------

`PixieConfig(root: str = 'pixie_qa', dataset_dir: str = 'pixie_qa/datasets', rate_limits: RateLimitConfig | None = None, trace_output: str | None = None, tracing_enabled: bool = False)`
:   Immutable configuration snapshot.
    
    All paths default to subdirectories / files within a single ``pixie_qa``
    project folder so that observations, datasets, tests, scripts and notes
    live in one predictable location.
    
    Attributes:
        root: Root directory for all pixie artefacts.
        dataset_dir: Directory for dataset JSON files.
        rate_limits: Optional evaluator rate limits loaded from ``PIXIE_RATE_LIMIT_*``.

    ### Instance variables

    `dataset_dir: str`
    :

    `rate_limits: pixie.config.RateLimitConfig | None`
    :

    `root: str`
    :

    `trace_output: str | None`
    :

    `tracing_enabled: bool`
    :

`RateLimitConfig(rps: float = 4.0, rpm: float = 50.0, tps: float = 10000.0, tpm: float = 500000.0)`
:   Configuration for evaluator rate limiting.
    
    Attributes:
        rps: Max requests per second.
        rpm: Max requests per minute.
        tps: Max tokens per second.
        tpm: Max tokens per minute.

    ### Instance variables

    `rpm: float`
    :

    `rps: float`
    :

    `tpm: float`
    :

    `tps: float`
    :