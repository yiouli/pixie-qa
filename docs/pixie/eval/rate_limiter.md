Module pixie.eval.rate_limiter
==============================
Central rate limiter for LLM evaluator calls.

Controls throughput using configurable RPS, RPM, TPS, and TPM limits.
Uses asyncio primitives (Semaphore + sliding window) so it integrates
naturally with the async evaluation pipeline.

Usage::

    from pixie.eval.rate_limiter import configure_rate_limits_from_config

    configure_rate_limits_from_config()

The module exposes a singleton via ``get_rate_limiter()``; when no
configuration has been applied the function returns ``None`` and
evaluator calls proceed without throttling.

Functions
---------

`configure_rate_limits(config: RateLimitConfig | None = None) ‑> None`
:   Set (or clear) the global rate limiter for evaluator calls.
    
    Pass a ``RateLimitConfig`` to enable rate limiting, or ``None`` to
    disable it.
    
    Args:
        config: The rate-limit configuration.  Passing ``None`` removes
            any previously configured limiter.

`configure_rate_limits_from_config(config: PixieConfig | None = None) ‑> None`
:   Apply the central Pixie config to the module-level rate limiter.

`get_rate_limiter() ‑> pixie.eval.rate_limiter.EvalRateLimiter | None`
:   Return the active rate limiter, auto-loading it from Pixie config once.

Classes
-------

`EvalRateLimiter(config: RateLimitConfig)`
:   Central rate limiter for LLM evaluator calls.
    
    Enforces both request-count and token-count limits using sliding
    windows.  All public methods are async and safe to call from
    concurrent ``asyncio.gather`` tasks.

    ### Instance variables

    `config: RateLimitConfig`
    :   Return the current configuration.

    ### Methods

    `acquire(self, estimated_tokens: int = 0) ‑> None`
    :   Wait until the request can proceed within rate limits.
        
        Blocks (with a short polling interval) until *all* four
        constraints (RPS, RPM, TPS, TPM) are satisfied, then records
        the request in the sliding windows.

    `estimate_tokens(self, text: str) ‑> int`
    :   Estimate token count using ``len(text) // 3`` approximation.

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