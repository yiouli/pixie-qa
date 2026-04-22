"""Tests for anonymous usage telemetry."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import NoReturn, cast
from urllib.request import Request

import pytest

import pixie.config
import pixie.telemetry as telemetry


class TestGetInstallId:
    def test_persists_stable_install_id(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        root = tmp_path / "pixie-root"
        monkeypatch.setenv("PIXIE_ROOT", str(root))

        first = telemetry._get_install_id()
        second = telemetry._get_install_id()

        assert first == second
        assert (root / "install_id").read_text(encoding="utf-8") == first
        assert uuid.UUID(first).version == 4

    def test_returns_unknown_when_config_lookup_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def boom() -> NoReturn:
            raise RuntimeError("boom")

        monkeypatch.setattr(
            pixie.config,
            "get_config",
            boom,
        )

        assert telemetry._get_install_id() == "unknown"


class TestEmit:
    def test_noops_when_telemetry_is_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PIXIE_NO_TELEMETRY", "1")

        started = False

        def fake_thread(*_args: object, **_kwargs: object) -> NoReturn:
            nonlocal started
            started = True
            raise AssertionError("thread should not be created")

        monkeypatch.setattr("pixie.telemetry.threading.Thread", fake_thread)

        telemetry.emit("pixie_test", {"version": "1.2.3"})

        assert started is False

    def test_starts_daemon_thread_with_posthog_payload(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("PIXIE_NO_TELEMETRY", raising=False)
        monkeypatch.setattr(telemetry, "_get_install_id", lambda: "install-123")

        requests: list[tuple[Request, float]] = []
        thread_state: dict[str, object] = {}

        def fake_urlopen(request: Request, timeout: float) -> object:
            requests.append((request, timeout))
            return object()

        class FakeThread:
            def __init__(self, *, target: object, daemon: bool) -> None:
                thread_state["target"] = target
                thread_state["daemon"] = daemon
                thread_state["started"] = False

            def start(self) -> None:
                thread_state["started"] = True
                target = thread_state["target"]
                assert callable(target)
                target()

        monkeypatch.setattr("pixie.telemetry.urllib.request.urlopen", fake_urlopen)
        monkeypatch.setattr("pixie.telemetry.threading.Thread", FakeThread)

        telemetry.emit("pixie_test", {"version": "9.9.9"})

        assert thread_state == {
            "target": thread_state["target"],
            "daemon": True,
            "started": True,
        }
        assert len(requests) == 1

        request, timeout = requests[0]
        assert request.data is not None
        payload = json.loads(cast(bytes, request.data).decode("utf-8"))
        assert request.full_url == telemetry.POSTHOG_ENDPOINT
        assert request.get_method() == "POST"
        assert request.headers["Content-type"] == "application/json"
        assert timeout == 3
        assert payload == {
            "api_key": telemetry.POSTHOG_API_KEY,
            "event": "pixie_test",
            "distinct_id": "install-123",
            "properties": {"version": "9.9.9"},
        }
