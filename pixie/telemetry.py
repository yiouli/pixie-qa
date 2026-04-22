"""Anonymous usage telemetry for pixie.

Sends lightweight, fire-and-forget events to PostHog so pixie can measure
high-level usage without collecting personal data.

Set ``PIXIE_NO_TELEMETRY=1`` to opt out.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.request
import uuid
from pathlib import Path

POSTHOG_ENDPOINT = "https://us.i.posthog.com/capture/"
POSTHOG_API_KEY = "phc_uvoRufYTVrwBBh9Jkf4LhQQq4KDRFiNR78vhg8ME8NmK"


def _get_install_id() -> str:
    """Return a stable anonymous install identifier.

    The identifier is generated once and persisted to
    ``<pixie_root>/install_id``. Any failure falls back to ``"unknown"``.
    """
    try:
        from pixie.config import get_config

        install_id_file = Path(get_config().root) / "install_id"
        install_id_file.parent.mkdir(parents=True, exist_ok=True)
        if install_id_file.exists():
            existing_id = install_id_file.read_text(encoding="utf-8").strip()
            if existing_id:
                return existing_id

        install_id = str(uuid.uuid4())
        install_id_file.write_text(install_id, encoding="utf-8")
        return install_id
    except Exception:
        return "unknown"


def emit(event: str, properties: dict[str, object] | None = None) -> None:
    """Emit an anonymous usage event.

    Telemetry is best-effort only: it never blocks the caller, never raises,
    and becomes a no-op when ``PIXIE_NO_TELEMETRY`` is set.
    """
    if os.environ.get("PIXIE_NO_TELEMETRY"):
        return

    payload = json.dumps(
        {
            "api_key": POSTHOG_API_KEY,
            "event": event,
            "distinct_id": _get_install_id(),
            "properties": properties or {},
        }
    ).encode("utf-8")

    def _send() -> None:
        try:
            request = urllib.request.Request(
                POSTHOG_ENDPOINT,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(request, timeout=3)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()
