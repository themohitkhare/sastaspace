"""System metrics via psutil + optional GPU (nvidia-smi / rocm-smi)."""

from __future__ import annotations

import subprocess
import time
from typing import Any

import psutil


def _gpu_nvidia() -> dict[str, Any] | None:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name",
                "--format=csv,noheader,nounits",
            ],
            timeout=3,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        if len(parts) < 5:
            return None
        return {
            "pct": int(parts[0]),
            "vram_used_mb": int(parts[1]),
            "vram_total_mb": int(parts[2]),
            "temp_c": int(parts[3]),
            "model": parts[4],
        }
    except Exception:  # noqa: BLE001
        return None


def _gpu_rocm() -> dict[str, Any] | None:
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showuse", "--showmeminfo", "vram", "--showtemp", "--json"],
            timeout=5,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        import json

        data = json.loads(out)
        # rocm-smi JSON structure varies by version; attempt best-effort parse
        card = next(iter(data.values())) if data else {}
        pct = int(float(card.get("GPU use (%)", card.get("GPU Use (%)", 0))))
        vram_used = int(card.get("VRAM Total Used Memory (B)", 0)) // (1024 * 1024)
        vram_total = int(card.get("VRAM Total Memory (B)", 0)) // (1024 * 1024)
        temp = int(float(card.get("Temperature (Sensor edge) (C)", card.get("Temperature (C)", 0))))
        return {
            "pct": pct,
            "vram_used_mb": vram_used,
            "vram_total_mb": vram_total,
            "temp_c": temp,
            "model": "AMD GPU",
        }
    except Exception:  # noqa: BLE001
        return None


def get_metrics() -> dict[str, Any]:
    cpu = psutil.cpu_percent(interval=None)
    cores = psutil.cpu_count(logical=True)

    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    disk = psutil.disk_usage("/")

    net = psutil.net_io_counters()
    boot_time = psutil.boot_time()
    uptime_s = int(time.time() - boot_time)

    result: dict[str, Any] = {
        "cpu": {"pct": round(cpu, 1), "cores": cores},
        "mem": {
            "used_gb": round(mem.used / 1e9, 2),
            "total_gb": round(mem.total / 1e9, 2),
            "pct": round(mem.percent, 1),
            "swap_used_mb": round(swap.used / 1e6),
            "swap_total_mb": round(swap.total / 1e6),
        },
        "disk": {
            "used_gb": round(disk.used / 1e9),
            "total_gb": round(disk.total / 1e9),
            "pct": round(disk.percent, 1),
            "mount": "/",
        },
        "net": {
            "tx_bytes": net.bytes_sent,
            "rx_bytes": net.bytes_recv,
        },
        "uptime_s": uptime_s,
    }

    gpu = _gpu_nvidia() or _gpu_rocm()
    if gpu:
        result["gpu"] = gpu

    return result
