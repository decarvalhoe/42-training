"""Tests for tmux pane capture (Issue #179) and session listing (Issue #178)."""

from __future__ import annotations

import asyncio
import subprocess
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Pane capture tests (Issue #179)
# ---------------------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_tmux_pane_returns_content():
    """Happy path: tmux session exists and content is captured."""

    async def fake_capture(*args, **kwargs):
        proc = AsyncMock()
        proc.returncode = 0
        if "capture-pane" in args:
            proc.communicate = AsyncMock(return_value=(b"$ whoami\nlearner\n$\n", b""))
        else:
            proc.communicate = AsyncMock(return_value=(b"24 80\n", b""))
        return proc

    with (
        patch("app.tmux.asyncio.create_subprocess_exec", side_effect=fake_capture),
        patch("app.tmux.shutil.which", return_value="/usr/bin/tmux"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/tmux/pane/my-session")

    assert resp.status_code == 200
    data = resp.json()
    assert data["session"] == "my-session"
    assert "whoami" in data["content"]
    assert data["rows"] == 24
    assert data["cols"] == 80
    assert "timestamp" in data


@pytest.mark.anyio
async def test_tmux_pane_session_not_found():
    """Returns 404 when the tmux session does not exist."""

    async def fake_capture(*args, **kwargs):
        proc = AsyncMock()
        proc.returncode = 1
        proc.communicate = AsyncMock(return_value=(b"", b"can't find session: nope\n"))
        return proc

    with (
        patch("app.tmux.asyncio.create_subprocess_exec", side_effect=fake_capture),
        patch("app.tmux.shutil.which", return_value="/usr/bin/tmux"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/tmux/pane/nope")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


@pytest.mark.anyio
async def test_tmux_not_available():
    """Returns 503 when tmux binary is not installed."""
    with patch("app.tmux.shutil.which", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/tmux/pane/any")

    assert resp.status_code == 503
    assert "not available" in resp.json()["detail"]


@pytest.mark.anyio
async def test_tmux_pane_timeout():
    """Returns 504 when tmux capture times out."""

    async def slow_capture(*args, **kwargs):
        proc = AsyncMock()
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
        return proc

    with (
        patch("app.tmux.asyncio.create_subprocess_exec", side_effect=slow_capture),
        patch("app.tmux.shutil.which", return_value="/usr/bin/tmux"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/tmux/pane/slow")

    assert resp.status_code == 504
    assert "timed out" in resp.json()["detail"]


@pytest.mark.anyio
async def test_tmux_pane_generic_error():
    """Returns 502 when tmux returns an unexpected error."""

    async def failing_capture(*args, **kwargs):
        proc = AsyncMock()
        proc.returncode = 1
        proc.communicate = AsyncMock(return_value=(b"", b"server exited unexpectedly\n"))
        return proc

    with (
        patch("app.tmux.asyncio.create_subprocess_exec", side_effect=failing_capture),
        patch("app.tmux.shutil.which", return_value="/usr/bin/tmux"),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/v1/tmux/pane/broken")

    assert resp.status_code == 502
    assert "tmux error" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Session listing tests (Issue #178)
# ---------------------------------------------------------------------------

_TMUX_OUTPUT = "rbok-gemini\t1711700000\t1711703600\t3\t1\nrbok-codex\t1711700000\t1711700100\t2\t0\n"


class TestTmuxSessions:
    def test_returns_sessions_from_tmux(self) -> None:
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=_TMUX_OUTPUT, stderr="")
        with patch("app.tmux.subprocess.run", return_value=result):
            r = client.get("/api/v1/tmux/sessions")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert len(data["sessions"]) == 2
        first = data["sessions"][0]
        assert first["name"] == "rbok-gemini"
        assert first["attached"] is True
        assert first["status"] == "active"
        assert first["windows"] == 3

    def test_tmux_not_installed(self) -> None:
        with patch("app.tmux.subprocess.run", side_effect=FileNotFoundError):
            r = client.get("/api/v1/tmux/sessions")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["sessions"] == []

    def test_tmux_returns_error(self) -> None:
        result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="no server running")
        with patch("app.tmux.subprocess.run", return_value=result):
            r = client.get("/api/v1/tmux/sessions")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0

    def test_tmux_timeout(self) -> None:
        with patch("app.tmux.subprocess.run", side_effect=subprocess.TimeoutExpired("tmux", 5)):
            r = client.get("/api/v1/tmux/sessions")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0

    def test_session_fields(self) -> None:
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=_TMUX_OUTPUT, stderr="")
        with patch("app.tmux.subprocess.run", return_value=result):
            r = client.get("/api/v1/tmux/sessions")
        session = r.json()["sessions"][0]
        assert set(session.keys()) == {"name", "status", "created_at", "last_activity", "windows", "attached"}

    def test_idle_detection(self) -> None:
        """A detached session with old activity should be idle."""
        old_line = "old-session\t1000000000\t1000000000\t1\t0\n"
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=old_line, stderr="")
        with patch("app.tmux.subprocess.run", return_value=result):
            r = client.get("/api/v1/tmux/sessions")
        session = r.json()["sessions"][0]
        assert session["status"] == "idle"
        assert session["attached"] is False

    def test_malformed_line_skipped(self) -> None:
        bad_output = "incomplete\tdata\n"
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=bad_output, stderr="")
        with patch("app.tmux.subprocess.run", return_value=result):
            r = client.get("/api/v1/tmux/sessions")
        assert r.json()["total"] == 0
