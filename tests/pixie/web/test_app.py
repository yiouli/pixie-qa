"""Tests for pixie.web.app — Starlette web UI application."""

from __future__ import annotations

import asyncio
import json
import unittest.mock
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from pixie.web.app import (
    SSEManager,
    _build_manifest,
    _list_datasets,
    _list_md_files,
    _list_results,
    _list_scorecards,
    create_app,
)

# ── Manifest helpers ─────────────────────────────────────────────────


class TestListMdFiles:
    def test_returns_sorted_markdown_files(self, tmp_path: Path) -> None:
        (tmp_path / "02-data-flow.md").write_text("# Data Flow")
        (tmp_path / "01-entry-point.md").write_text("# Entry")
        (tmp_path / "not-md.txt").write_text("skip")

        result = _list_md_files(tmp_path)
        assert len(result) == 2
        assert result[0]["name"] == "01-entry-point.md"
        assert result[1]["name"] == "02-data-flow.md"

    def test_returns_empty_for_missing_dir(self, tmp_path: Path) -> None:
        result = _list_md_files(tmp_path / "nonexistent")
        assert result == []


class TestListDatasets:
    def test_returns_dataset_json_files(self, tmp_path: Path) -> None:
        ds_dir = tmp_path / "datasets"
        ds_dir.mkdir()
        (ds_dir / "faq.json").write_text("{}")
        (ds_dir / "notes.txt").write_text("skip")

        result = _list_datasets(tmp_path)
        assert len(result) == 1
        assert result[0]["name"] == "faq"
        assert result[0]["path"] == "datasets/faq.json"

    def test_returns_empty_when_no_datasets_dir(self, tmp_path: Path) -> None:
        result = _list_datasets(tmp_path)
        assert result == []


class TestListScorecards:
    def test_returns_scorecards_newest_first(self, tmp_path: Path) -> None:
        sc_dir = tmp_path / "scorecards"
        sc_dir.mkdir()
        (sc_dir / "20250101-scorecard.html").write_text("<html/>")
        (sc_dir / "20250201-scorecard.html").write_text("<html/>")

        result = _list_scorecards(tmp_path)
        assert len(result) == 2
        # Newest first (reverse sort)
        assert result[0]["name"] == "20250201-scorecard"
        assert result[1]["name"] == "20250101-scorecard"


class TestBuildManifest:
    def test_builds_complete_manifest(self, tmp_path: Path) -> None:
        (tmp_path / "01-entry.md").write_text("# Entry")
        (tmp_path / "datasets").mkdir()
        (tmp_path / "datasets" / "test.json").write_text("{}")
        (tmp_path / "scorecards").mkdir()
        (tmp_path / "scorecards" / "sc.html").write_text("<html/>")

        manifest = _build_manifest(tmp_path)
        assert len(manifest["markdown_files"]) == 1  # type: ignore[arg-type]
        assert len(manifest["datasets"]) == 1  # type: ignore[arg-type]
        assert len(manifest["scorecards"]) == 1  # type: ignore[arg-type]

    def test_manifest_includes_results(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results" / "20260403-120000"
        results_dir.mkdir(parents=True)
        (results_dir / "result.json").write_text("{}")

        manifest = _build_manifest(tmp_path)
        assert len(manifest["results"]) == 1  # type: ignore[arg-type]


class TestListResults:
    def test_returns_result_directories(self, tmp_path: Path) -> None:
        results_dir = tmp_path / "results" / "20260403-120000"
        results_dir.mkdir(parents=True)
        (results_dir / "result.json").write_text("{}")

        result = _list_results(tmp_path)
        assert len(result) == 1
        assert result[0]["name"] == "20260403-120000"
        assert result[0]["path"] == "results/20260403-120000"

    def test_ignores_dirs_without_result_json(self, tmp_path: Path) -> None:
        (tmp_path / "results" / "orphan").mkdir(parents=True)
        assert _list_results(tmp_path) == []

    def test_empty_when_no_dir(self, tmp_path: Path) -> None:
        assert _list_results(tmp_path) == []


# ── SSEManager ───────────────────────────────────────────────────────


class TestSSEManager:
    def test_subscribe_and_unsubscribe(self) -> None:
        mgr = SSEManager()
        assert not mgr.has_subscribers()

        q = mgr.subscribe()
        assert mgr.has_subscribers()

        mgr.unsubscribe(q)
        assert not mgr.has_subscribers()

    def test_subscriber_count(self) -> None:
        mgr = SSEManager()
        assert mgr.subscriber_count == 0

        q1 = mgr.subscribe()
        assert mgr.subscriber_count == 1

        q2 = mgr.subscribe()
        assert mgr.subscriber_count == 2

        mgr.unsubscribe(q1)
        assert mgr.subscriber_count == 1

        mgr.unsubscribe(q2)
        assert mgr.subscriber_count == 0

    def test_unsubscribe_nonexistent_is_safe(self) -> None:
        mgr = SSEManager()
        q: asyncio.Queue[str] = asyncio.Queue()
        mgr.unsubscribe(q)  # Should not raise

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_subscribers(self) -> None:
        mgr = SSEManager()
        q1 = mgr.subscribe()
        q2 = mgr.subscribe()

        await mgr.broadcast("test", {"key": "value"})

        msg1 = q1.get_nowait()
        msg2 = q2.get_nowait()
        assert "event: test" in msg1
        assert '"key": "value"' in msg1
        assert msg1 == msg2


# ── Starlette App Endpoints ─────────────────────────────────────────


class TestAppEndpoints:
    @pytest.fixture()
    def app_root(self, tmp_path: Path) -> Path:
        (tmp_path / "01-entry.md").write_text("# Entry Point")
        ds = tmp_path / "datasets"
        ds.mkdir()
        (ds / "faq.json").write_text(json.dumps({"name": "faq", "items": []}))
        sc = tmp_path / "scorecards"
        sc.mkdir()
        (sc / "20250101-test.html").write_text("<html><body>scorecard</body></html>")
        return tmp_path

    @pytest.fixture()
    def client(self, app_root: Path) -> TestClient:
        app = create_app(str(app_root))
        return TestClient(app)

    def test_index_serves_webui_html(self, client: TestClient) -> None:
        with patch("pixie.web.app._load_webui_html", return_value="<html>webui</html>"):
            resp = client.get("/")
        assert resp.status_code == 200
        assert "webui" in resp.text

    def test_index_returns_500_when_not_built(self, client: TestClient) -> None:
        with patch("pixie.web.app._load_webui_html", side_effect=FileNotFoundError):
            resp = client.get("/")
        assert resp.status_code == 500
        assert "not built" in resp.text

    def test_manifest_endpoint(self, client: TestClient) -> None:
        resp = client.get("/api/manifest")
        assert resp.status_code == 200
        data = resp.json()
        assert "markdown_files" in data
        assert "datasets" in data
        assert "scorecards" in data
        assert len(data["markdown_files"]) == 1
        assert len(data["datasets"]) == 1
        assert len(data["scorecards"]) == 1

    def test_file_endpoint_markdown(self, client: TestClient) -> None:
        resp = client.get("/api/file?path=01-entry.md")
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "# Entry Point"

    def test_file_endpoint_json(self, client: TestClient) -> None:
        resp = client.get("/api/file?path=datasets/faq.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "faq"

    def test_file_endpoint_html(self, client: TestClient) -> None:
        resp = client.get("/api/file?path=scorecards/20250101-test.html")
        assert resp.status_code == 200
        assert "scorecard" in resp.text

    def test_file_endpoint_missing_path(self, client: TestClient) -> None:
        resp = client.get("/api/file")
        assert resp.status_code == 400

    def test_file_endpoint_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/file?path=nonexistent.md")
        assert resp.status_code == 404

    def test_file_endpoint_path_traversal_blocked(self, client: TestClient) -> None:
        resp = client.get("/api/file?path=../../../etc/passwd")
        assert resp.status_code == 403

    def test_file_endpoint_unsupported_type(
        self, client: TestClient, app_root: Path
    ) -> None:
        (app_root / "test.py").write_text("print('hello')")
        resp = client.get("/api/file?path=test.py")
        assert resp.status_code == 400

    def test_status_endpoint_returns_active_clients(self, client: TestClient) -> None:
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "active_clients" in data
        assert data["active_clients"] == 0

    def test_result_endpoint_returns_data(
        self, client: TestClient, app_root: Path
    ) -> None:
        result_dir = app_root / "results" / "20260403-120000"
        result_dir.mkdir(parents=True)
        result_data = {
            "meta": {"testId": "20260403-120000"},
            "datasets": [{"dataset": "test", "entries": []}],
        }
        (result_dir / "result.json").write_text(json.dumps(result_data))

        resp = client.get("/api/result?id=20260403-120000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["testId"] == "20260403-120000"

    def test_result_endpoint_merges_analysis(
        self, client: TestClient, app_root: Path
    ) -> None:
        result_dir = app_root / "results" / "20260403-120000"
        result_dir.mkdir(parents=True)
        result_data = {
            "meta": {"testId": "20260403-120000"},
            "datasets": [{"dataset": "test", "entries": []}],
        }
        (result_dir / "result.json").write_text(json.dumps(result_data))
        (result_dir / "dataset-0.md").write_text("## Analysis\nAll good.")

        resp = client.get("/api/result?id=20260403-120000")
        data = resp.json()
        assert data["datasets"][0]["analysis"] == "## Analysis\nAll good."

    def test_result_endpoint_missing_id(self, client: TestClient) -> None:
        resp = client.get("/api/result")
        assert resp.status_code == 400

    def test_result_endpoint_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/result?id=nonexistent")
        assert resp.status_code == 404

    def test_result_endpoint_path_traversal_blocked(self, client: TestClient) -> None:
        resp = client.get("/api/result?id=../../etc/passwd")
        assert resp.status_code == 404

    def test_manifest_includes_results(
        self, client: TestClient, app_root: Path
    ) -> None:
        result_dir = app_root / "results" / "20260403-120000"
        result_dir.mkdir(parents=True)
        (result_dir / "result.json").write_text("{}")

        resp = client.get("/api/manifest")
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 1


# ── CLI Start Command ────────────────────────────────────────────────


class TestStartCommand:
    def test_start_calls_init_and_run_server(self) -> None:
        with (
            patch("pixie.cli.start_command.init_pixie_dir") as mock_init,
            patch("pixie.cli.start_command.run_server") as mock_run,
        ):
            from pixie.cli.start_command import start

            result = start(root="/tmp/test-root")
            assert result == 0
            mock_init.assert_called_once_with(root="/tmp/test-root")
            mock_run.assert_called_once_with("/tmp/test-root", tab=None, item_id=None)

    def test_start_uses_config_default(self) -> None:
        with (
            patch("pixie.cli.start_command.init_pixie_dir") as mock_init,
            patch("pixie.cli.start_command.run_server") as mock_run,
            patch("pixie.cli.start_command.get_config") as mock_config,
        ):
            mock_config.return_value.root = "pixie_qa"
            from pixie.cli.start_command import start

            start(root=None)
            mock_init.assert_called_once_with(root="pixie_qa")
            mock_run.assert_called_once_with("pixie_qa", tab=None, item_id=None)

    def test_start_passes_tab_and_item_id(self) -> None:
        with (
            patch("pixie.cli.start_command.init_pixie_dir") as mock_init,
            patch("pixie.cli.start_command.run_server") as mock_run,
        ):
            from pixie.cli.start_command import start

            start(root="/tmp/r", tab="scorecards", item_id="scorecards/sc.html")
            mock_init.assert_called_once_with(root="/tmp/r")
            mock_run.assert_called_once_with(
                "/tmp/r", tab="scorecards", item_id="scorecards/sc.html"
            )


# ── CLI Main Integration ────────────────────────────────────────────


class TestMainStartSubcommand:
    def test_pixie_start_routes_to_start_command(self) -> None:
        with patch("pixie.cli.start_command.start", return_value=0) as mock_start:
            from pixie.cli.main import main

            result = main(["start"])
            assert result == 0
            mock_start.assert_called_once_with(root=None)

    def test_pixie_start_with_root_arg(self) -> None:
        with patch("pixie.cli.start_command.start", return_value=0) as mock_start:
            from pixie.cli.main import main

            result = main(["start", "/tmp/my-root"])
            assert result == 0
            mock_start.assert_called_once_with(root="/tmp/my-root")


class TestMainInitSubcommand:
    def test_pixie_init_routes_to_init_only(self) -> None:
        with patch("pixie.cli.init_command.init_pixie_dir") as mock_init:
            mock_init.return_value = Path("pixie_qa")
            from pixie.cli.main import main

            result = main(["init"])
            assert result == 0
            mock_init.assert_called_once_with(root=None)

    def test_pixie_init_with_root_routes_to_init_only(self) -> None:
        with patch("pixie.cli.init_command.init_pixie_dir") as mock_init:
            mock_init.return_value = Path("/tmp/my-root")
            from pixie.cli.main import main

            result = main(["init", "/tmp/my-root"])
            assert result == 0
            mock_init.assert_called_once_with(root="/tmp/my-root")


# ── build_url ────────────────────────────────────────────────────────


class TestBuildUrl:
    def test_plain_url(self) -> None:
        from pixie.web.server import build_url

        assert build_url("127.0.0.1", 7118) == "http://127.0.0.1:7118"

    def test_with_tab(self) -> None:
        from pixie.web.server import build_url

        url = build_url("127.0.0.1", 7118, tab="scorecards")
        assert url == "http://127.0.0.1:7118?tab=scorecards"

    def test_with_tab_and_id(self) -> None:
        from pixie.web.server import build_url

        url = build_url(
            "127.0.0.1", 7118, tab="scorecards", item_id="scorecards/sc.html"
        )
        assert url == "http://127.0.0.1:7118?tab=scorecards&id=scorecards/sc.html"

    def test_no_params_when_none(self) -> None:
        from pixie.web.server import build_url

        url = build_url("127.0.0.1", 7118, tab=None, item_id=None)
        assert "?" not in url


# ── open_webui ───────────────────────────────────────────────────────


class TestOpenWebui:
    def test_sends_navigate_when_active_clients(self) -> None:
        """When the server has active SSE clients, send navigate instead of opening browser."""
        from pixie.web.server import open_webui

        with (
            patch("pixie.web.server._is_server_running", return_value=7118),
            patch("pixie.web.server._probe_server", return_value=1),
            patch("pixie.web.server._send_navigate") as mock_nav,
            patch("pixie.web.server.webbrowser.open") as mock_open,
        ):
            open_webui("/tmp/root", tab="scorecards", item_id="scorecards/x.html")
            mock_nav.assert_called_once_with(
                "127.0.0.1", 7118, tab="scorecards", item_id="scorecards/x.html"
            )
            mock_open.assert_not_called()

    def test_opens_browser_when_no_active_clients(self) -> None:
        """When the server is running but has no active clients, open browser."""
        from pixie.web.server import open_webui

        with (
            patch("pixie.web.server._is_server_running", return_value=7118),
            patch("pixie.web.server._probe_server", return_value=0),
            patch("pixie.web.server._send_navigate") as mock_nav,
            patch("pixie.web.server.webbrowser.open") as mock_open,
        ):
            open_webui("/tmp/root", tab="scorecards", item_id="scorecards/x.html")
            mock_open.assert_called_once()
            url = mock_open.call_args[0][0]
            assert "tab=scorecards" in url
            assert "id=scorecards/x.html" in url
            mock_nav.assert_not_called()

    def test_opens_browser_on_lock_port(self) -> None:
        """When the server is running on a non-default port, use that port."""
        from pixie.web.server import open_webui

        with (
            patch("pixie.web.server._is_server_running", return_value=9999),
            patch("pixie.web.server._probe_server", return_value=0),
            patch("pixie.web.server.webbrowser.open") as mock_open,
        ):
            open_webui("/tmp/root", tab="scorecards")
            url = mock_open.call_args[0][0]
            assert ":9999" in url

    def test_starts_server_in_background_when_not_running(self) -> None:
        from pixie.web.server import open_webui

        with (
            patch("pixie.web.server._is_server_running", return_value=None),
            patch("pixie.web.server._read_lock", return_value=None),
            patch("threading.Thread") as mock_thread_cls,
            patch("pixie.web.server.webbrowser.open") as mock_open,
            patch("time.sleep"),
        ):
            mock_thread = mock_thread_cls.return_value
            open_webui("/tmp/root", tab="datasets", item_id="datasets/faq.json")

            # Server started in a daemon thread
            mock_thread_cls.assert_called_once()
            assert mock_thread_cls.call_args[1]["daemon"] is True
            mock_thread.start.assert_called_once()

            # Browser opened
            mock_open.assert_called_once()
            url = mock_open.call_args[0][0]
            assert "tab=datasets" in url


# ── pixie test → web UI integration ─────────────────────────────────


class TestPixieTestOpensWebUI:
    def test_pixie_test_calls_open_webui_with_scorecard(self, tmp_path: Path) -> None:
        """After generating a scorecard, pixie test calls open_webui."""
        from pixie.cli.test_command import main as pixie_test_main

        # Create a minimal dataset with a built-in evaluator
        dataset_dir = tmp_path / "datasets"
        dataset_dir.mkdir()
        dataset_file = dataset_dir / "test-qa.json"
        dataset_file.write_text(
            json.dumps(
                {
                    "name": "test-qa",
                    "items": [
                        {
                            "eval_input": "What is 1+1?",
                            "eval_output": "2",
                            "expected_output": "2",
                            "evaluators": ["ExactMatch"],
                        }
                    ],
                }
            )
        )
        pixie_root = tmp_path / "pixie_qa"

        with (
            patch("pixie.web.server.open_webui") as mock_open,
            patch.dict("os.environ", {"PIXIE_ROOT": str(pixie_root)}),
        ):
            pixie_test_main([str(dataset_file)])

            mock_open.assert_called_once()
            call_args = mock_open.call_args
            assert call_args[1]["tab"] == "results"
            assert "results/" in call_args[1]["item_id"]

    def test_pixie_test_no_open_skips_webui(self, tmp_path: Path) -> None:
        """--no-open flag suppresses web UI opening."""
        from pixie.cli.test_command import main as pixie_test_main

        dataset_dir = tmp_path / "datasets"
        dataset_dir.mkdir()
        dataset_file = dataset_dir / "test-qa.json"
        dataset_file.write_text(
            json.dumps(
                {
                    "name": "test-qa",
                    "items": [
                        {
                            "eval_input": "What is 1+1?",
                            "eval_output": "2",
                            "expected_output": "2",
                            "evaluators": ["ExactMatch"],
                        }
                    ],
                }
            )
        )
        pixie_root = tmp_path / "pixie_qa"

        with (
            patch("pixie.web.server.open_webui") as mock_open,
            patch.dict("os.environ", {"PIXIE_ROOT": str(pixie_root)}),
        ):
            pixie_test_main([str(dataset_file), "--no-open"])
            mock_open.assert_not_called()


# ── Server lock file ────────────────────────────────────────────────


class TestServerLock:
    def test_write_and_read_lock(self, tmp_path: Path) -> None:
        from pixie.web.server import _read_lock, _write_lock

        root = str(tmp_path)
        _write_lock(root, 7200)
        assert _read_lock(root) == 7200

    def test_read_lock_returns_none_when_missing(self, tmp_path: Path) -> None:
        from pixie.web.server import _read_lock

        assert _read_lock(str(tmp_path)) is None

    def test_remove_lock(self, tmp_path: Path) -> None:
        from pixie.web.server import _read_lock, _remove_lock, _write_lock

        root = str(tmp_path)
        _write_lock(root, 7200)
        _remove_lock(root)
        assert _read_lock(root) is None

    def test_remove_lock_when_missing_is_safe(self, tmp_path: Path) -> None:
        from pixie.web.server import _remove_lock

        _remove_lock(str(tmp_path))  # Should not raise

    def test_is_server_running_with_active_lock(self, tmp_path: Path) -> None:
        from pixie.web.server import _is_server_running, _write_lock

        root = str(tmp_path)
        _write_lock(root, 7118)
        with patch("pixie.web.server._probe_server", return_value=0):
            assert _is_server_running(root) == 7118

    def test_is_server_running_cleans_stale_lock(self, tmp_path: Path) -> None:
        from pixie.web.server import _is_server_running, _read_lock, _write_lock

        root = str(tmp_path)
        _write_lock(root, 7118)
        with patch("pixie.web.server._probe_server", return_value=None):
            assert _is_server_running(root) is None
        # Stale lock should have been cleaned up
        assert _read_lock(root) is None

    def test_is_server_running_no_lock(self, tmp_path: Path) -> None:
        from pixie.web.server import _is_server_running

        assert _is_server_running(str(tmp_path)) is None


# ── _probe_server ──────────────────────────────────────────────────────


class TestProbeServer:
    def test_returns_client_count_on_success(self) -> None:
        from pixie.web.server import _probe_server

        response_body = json.dumps({"active_clients": 3}).encode()
        mock_resp = unittest.mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)

        with patch("pixie.web.server.urllib.request.urlopen", return_value=mock_resp):
            assert _probe_server("127.0.0.1", 7118) == 3

    def test_returns_none_on_connection_error(self) -> None:
        from pixie.web.server import _probe_server

        with patch(
            "pixie.web.server.urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            assert _probe_server("127.0.0.1", 7118) is None

    def test_returns_none_on_timeout(self) -> None:
        from pixie.web.server import _probe_server

        with patch(
            "pixie.web.server.urllib.request.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            assert _probe_server("127.0.0.1", 7118) is None


# ── get_server_status ──────────────────────────────────────────────────


class TestGetServerStatus:
    def test_not_running_when_no_lock(self, tmp_path: Path) -> None:
        from pixie.web.server import ServerStatus, get_server_status

        status = get_server_status(str(tmp_path))
        assert status == ServerStatus(running=False, port=None, active_clients=0)

    def test_not_running_when_stale_lock(self, tmp_path: Path) -> None:
        from pixie.web.server import ServerStatus, _write_lock, get_server_status

        root = str(tmp_path)
        _write_lock(root, 7118)
        with patch("pixie.web.server._probe_server", return_value=None):
            status = get_server_status(root)
        assert status == ServerStatus(running=False, port=None, active_clients=0)
        # Stale lock should be cleaned
        from pixie.web.server import _read_lock

        assert _read_lock(root) is None

    def test_running_with_no_clients(self, tmp_path: Path) -> None:
        from pixie.web.server import ServerStatus, _write_lock, get_server_status

        root = str(tmp_path)
        _write_lock(root, 7118)
        with patch("pixie.web.server._probe_server", return_value=0):
            status = get_server_status(root)
        assert status == ServerStatus(running=True, port=7118, active_clients=0)

    def test_running_with_active_clients(self, tmp_path: Path) -> None:
        from pixie.web.server import ServerStatus, _write_lock, get_server_status

        root = str(tmp_path)
        _write_lock(root, 9999)
        with patch("pixie.web.server._probe_server", return_value=5):
            status = get_server_status(root)
        assert status == ServerStatus(running=True, port=9999, active_clients=5)
