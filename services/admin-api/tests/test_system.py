"""Tests for system metrics endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("SPACETIME_TOKEN", "test-token")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://admin.sastaspace.com")

    from sastaspace_admin_api.main import app

    with TestClient(app) as c:
        yield c


def _mock_psutil():
    cpu = MagicMock()
    cpu.percent = 42.1
    cpu.count = MagicMock(return_value=16)

    mem = MagicMock()
    mem.used = 9_200_000_000
    mem.total = 32_000_000_000
    mem.percent = 28.7

    swap = MagicMock()
    swap.used = 0
    swap.total = 2_147_483_648

    disk = MagicMock()
    disk.used = 145_000_000_000
    disk.total = 500_000_000_000
    disk.percent = 29.0

    net = MagicMock()
    net.bytes_sent = 1_234_567
    net.bytes_recv = 9_876_543

    return cpu, mem, swap, disk, net


def test_system_shape(client):
    cpu, mem, swap, disk, net = _mock_psutil()

    with (
        patch("psutil.cpu_percent", return_value=42.1),
        patch("psutil.cpu_count", return_value=16),
        patch("psutil.virtual_memory", return_value=mem),
        patch("psutil.swap_memory", return_value=swap),
        patch("psutil.disk_usage", return_value=disk),
        patch("psutil.net_io_counters", return_value=net),
        patch("psutil.boot_time", return_value=0.0),
        patch("subprocess.check_output", side_effect=FileNotFoundError),
    ):
        resp = client.get("/system")

    assert resp.status_code == 200
    data = resp.json()
    assert "cpu" in data
    assert "mem" in data
    assert "disk" in data
    assert "net" in data
    assert "uptime_s" in data
    assert data["cpu"]["cores"] == 16
    assert isinstance(data["cpu"]["pct"], float)
    assert isinstance(data["mem"]["total_gb"], float)
    assert isinstance(data["disk"]["pct"], float)
    # gpu is absent when neither nvidia-smi nor rocm-smi is available
    assert "gpu" not in data


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
