"""Tests for pixie.web.app — Starlette web UI application."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from pixie.web.app import (
    SSEManager,
    _build_manifest,
    _list_datasets,
    _list_md_files,
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


# ── SSEManager ───────────────────────────────────────────────────────


class TestSSEManager:
    def test_subscribe_and_unsubscribe(self) -> None:
        mgr = SSEManager()
        assert not mgr.has_subscribers()

        q = mgr.subscribe()
        assert mgr.has_subscribers()

        mgr.unsubscribe(q)
        assert not mgr.has_subscribers()

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


# ── CLI Start Command ────────────────────────────────────────────────


class TestStartCommand:
    def test_start_calls_run_server(self) -> None:
        with patch("pixie.cli.start_command.run_server") as mock_run:
            from pixie.cli.start_command import start

            result = start(root="/tmp/test-root")
            assert result == 0
            mock_run.assert_called_once_with("/tmp/test-root", tab=None, item_id=None)

    def test_start_uses_config_default(self) -> None:
        with (
            patch("pixie.cli.start_command.run_server") as mock_run,
            patch("pixie.cli.start_command.get_config") as mock_config,
        ):
            mock_config.return_value.root = "pixie_qa"
            from pixie.cli.start_command import start

            start(root=None)
            mock_run.assert_called_once_with("pixie_qa", tab=None, item_id=None)

    def test_start_passes_tab_and_item_id(self) -> None:
        with patch("pixie.cli.start_command.run_server") as mock_run:
            from pixie.cli.start_command import start

            start(root="/tmp/r", tab="scorecards", item_id="scorecards/sc.html")
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
    def test_pixie_init_routes_to_init_and_start(self) -> None:
        with (
            patch("pixie.cli.init_command.init_pixie_dir") as mock_init,
            patch("pixie.cli.start_command.start", return_value=0) as mock_start,
        ):
            mock_init.return_value = Path("pixie_qa")
            from pixie.cli.main import main

            result = main(["init"])
            assert result == 0
            mock_init.assert_called_once_with(root=None)
            mock_start.assert_called_once_with(root=None)

    def test_pixie_init_with_root_routes_to_init_and_start(self) -> None:
        with (
            patch("pixie.cli.init_command.init_pixie_dir") as mock_init,
            patch("pixie.cli.start_command.start", return_value=0) as mock_start,
        ):
            mock_init.return_value = Path("/tmp/my-root")
            from pixie.cli.main import main

            result = main(["init", "/tmp/my-root"])
            assert result == 0
            mock_init.assert_called_once_with(root="/tmp/my-root")
            mock_start.assert_called_once_with(root="/tmp/my-root")


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
    def test_opens_browser_when_server_running(self) -> None:
        from pixie.web.server import open_webui

        with (
            patch("pixie.web.server._is_port_in_use", return_value=True),
            patch("pixie.web.server.webbrowser.open") as mock_open,
        ):
            open_webui("/tmp/root", tab="scorecards", item_id="scorecards/x.html")
            mock_open.assert_called_once()
            url = mock_open.call_args[0][0]
            assert "tab=scorecards" in url
            assert "id=scorecards/x.html" in url

    def test_starts_server_in_background_when_not_running(self) -> None:
        from pixie.web.server import open_webui

        with (
            patch("pixie.web.server._is_port_in_use", return_value=False),
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

        # Create a minimal test file that always passes
        test_file = tmp_path / "test_pass.py"
        test_file.write_text("async def test_ok():\n    pass\n")
        pixie_root = tmp_path / "pixie_qa"

        with (
            patch("pixie.web.server.open_webui") as mock_open,
            patch.dict("os.environ", {"PIXIE_ROOT": str(pixie_root)}),
        ):
            pixie_test_main([str(test_file)])

            mock_open.assert_called_once()
            call_args = mock_open.call_args
            assert call_args[1]["tab"] == "scorecards"
            assert "scorecards/" in call_args[1]["item_id"]

    def test_pixie_test_no_open_skips_webui(self, tmp_path: Path) -> None:
        """--no-open flag suppresses web UI opening."""
        from pixie.cli.test_command import main as pixie_test_main

        test_file = tmp_path / "test_pass.py"
        test_file.write_text("async def test_ok():\n    pass\n")
        pixie_root = tmp_path / "pixie_qa"

        with (
            patch("pixie.web.server.open_webui") as mock_open,
            patch.dict("os.environ", {"PIXIE_ROOT": str(pixie_root)}),
        ):
            pixie_test_main([str(test_file), "--no-open"])
            mock_open.assert_not_called()
