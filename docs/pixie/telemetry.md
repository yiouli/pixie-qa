Module pixie.telemetry
======================
Anonymous usage telemetry for pixie.

Sends lightweight, fire-and-forget events to PostHog so pixie can measure
high-level usage without collecting personal data.

Set ``PIXIE_NO_TELEMETRY=1`` to opt out.

Functions
---------

`def emit(event: str, properties: dict[str, object] | None = None) ‑> None`
:   Emit an anonymous usage event.
    
    Telemetry is best-effort only: it never blocks the caller, never raises,
    and becomes a no-op when ``PIXIE_NO_TELEMETRY`` is set.