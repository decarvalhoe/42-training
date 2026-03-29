"""Tests for the tmux pane capture endpoint (Issue #179)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


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
