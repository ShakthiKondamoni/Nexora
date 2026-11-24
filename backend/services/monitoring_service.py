
"""Read-only host metrics, NVIDIA reporting and process enumeration."""

import os
import shutil
import subprocess

import psutil
import requests

from backend.services.settings_service import ollama_url


def num(x):
    """Convert a value to float, returning None if conversion fails."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _run_hidden(command, **kwargs):
    """Run a subprocess without opening a console window on Windows."""
    if os.name == "nt":
        kwargs["creationflags"] = (
            kwargs.get("creationflags", 0)
            | subprocess.CREATE_NO_WINDOW
        )

        # Additional protection against briefly displaying a console.
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = startupinfo

    return subprocess.run(command, **kwargs)


def gpu():
    """Return NVIDIA GPU metrics, or an error if unavailable."""
    if not shutil.which("nvidia-smi"):
        return None, "nvidia-smi not found (no NVIDIA driver on PATH)"

    try:
        result = _run_hidden(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,"
                "memory.total,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

        if result.returncode != 0:
            error = result.stderr.strip() or (
                f"nvidia-smi exited with code {result.returncode}"
            )
            return None, f"nvidia-smi failed: {error}"

        lines = result.stdout.strip().splitlines()
        if not lines:
            return None, "nvidia-smi returned no GPU information"

        values = [value.strip() for value in lines[0].split(",")]

        if len(values) < 6:
            return None, "nvidia-smi returned incomplete GPU information"

        used_mb = num(values[2])
        total_mb = num(values[3])

        return {
            "name": values[0],
            "util": num(values[1]),
            "used": used_mb * (2**20) if used_mb is not None else None,
            "total": total_mb * (2**20) if total_mb is not None else None,
            "temp": num(values[4]),
            "power": num(values[5]),
        }, None

    except subprocess.TimeoutExpired:
        return None, "nvidia-smi timed out"
    except (OSError, ValueError, IndexError) as exc:
        return None, f"nvidia-smi failed: {exc}"


def metrics():
    """Collect system metrics and currently running Ollama models."""
    vm = psutil.virtual_memory()
    du = psutil.disk_usage(os.path.abspath(os.sep))
    gpu_data, gpu_error = gpu()

    try:
        response = requests.get(
            ollama_url() + "/api/ps",
            timeout=1.5,
        )
        response.raise_for_status()
        data = response.json()

        running_models = [
            {
                "name": model["name"],
                "size": model["size"],
                "vram": model.get("size_vram"),
                "ctx": model.get("context_length"),
            }
            for model in data.get("models", [])
        ]
        ollama_up = True

    except (requests.RequestException, ValueError, TypeError, KeyError):
        running_models = []
        ollama_up = False

    return {
        "cpu": psutil.cpu_percent(),
        "cores": psutil.cpu_count(),
        "ram": {
            "pct": vm.percent,
            "used": vm.used,
            "total": vm.total,
            "avail": vm.available,
        },
        "disk": {
            "pct": du.percent,
            "used": du.used,
            "total": du.total,
        },
        "gpu": gpu_data,
        "gpu_err": gpu_error,
        "ollama": {
            "up": ollama_up,
            "running": running_models,
        },
    }


def procs():
    """Enumerate processes and report their resource usage."""
    out = []

    for process in psutil.process_iter(
        ["pid", "name", "cpu_percent", "memory_info", "status"]
    ):
        try:
            info = process.info
            name = info["name"] or "?"
            memory_info = info["memory_info"]

            out.append(
                {
                    "pid": info["pid"],
                    "name": name,
                    "cpu": info["cpu_percent"] or 0,
                    "mem": memory_info.rss if memory_info else 0,
                    "status": info["status"],
                    "ai": "ollama" in name.lower(),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Processes can disappear or become inaccessible during enumeration.
            continue

    return out
