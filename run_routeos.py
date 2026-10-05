#!/usr/bin/env python3
"""Run the local backend from any folder.

The launcher stops an older RouteOS server, selects the project environment,
and can connect a USB Android device with ``--adb-reverse``.
"""

from __future__ import annotations

import argparse
import os
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
VENV_PYTHON = BACKEND / ".venv" / "bin" / "python"


def existing_backend_processes() -> list[int]:
    """Find RouteOS Uvicorn processes without requiring an extra dependency.
    Scans /proc for a uvicorn command running the `app:app` module from this
    repo's backend directory (no psutil needed).
    """
    processes: list[int] = []
    proc_root = Path("/proc")
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            working_directory = (entry / "cwd").resolve()
        except (OSError, UnicodeError):
            continue
        routeos_module = "app:app" in command and (
            working_directory == BACKEND
            or "backend.app:app" in command
            or str(BACKEND) in command
        )
        if "uvicorn" in command and routeos_module:
            processes.append(pid)
    return processes


def stop_existing_backends() -> None:
    """SIGTERM stale backends, wait up to 5 s, then SIGKILL any survivors."""
    processes = existing_backend_processes()
    if not processes:
        return

    print(f"Stopping existing RouteOS backend process(es): {', '.join(map(str, processes))}")
    for pid in processes:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.monotonic() + 5
    remaining = set(processes)
    while remaining and time.monotonic() < deadline:
        remaining = {pid for pid in remaining if Path(f"/proc/{pid}").exists()}
        if remaining:
            time.sleep(0.1)

    for pid in remaining:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def main() -> int:
    """Parse flags, prepare the environment, and run uvicorn in the foreground."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="reload after backend source changes")
    parser.add_argument(
        "--production-auth",
        action="store_true",
        help="disable development quick-login (password authentication only)",
    )
    parser.add_argument(
        "--adb-reverse",
        action="store_true",
        help="forward the backend port to a connected Android device",
    )
    args = parser.parse_args()

    if not BACKEND.is_dir():
        parser.error(f"backend directory not found: {BACKEND}")

    stop_existing_backends()

    python = VENV_PYTHON if VENV_PYTHON.is_file() else Path(sys.executable)
    if not VENV_PYTHON.is_file():
        print(
            "Warning: backend/.venv was not found; using the current Python interpreter.",
            file=sys.stderr,
        )

    if args.adb_reverse:
        adb = shutil.which("adb")
        if adb is None:
            parser.error("--adb-reverse requires adb on PATH")
        subprocess.run([adb, "reverse", f"tcp:{args.port}", f"tcp:{args.port}"], check=True)

    environment = os.environ.copy()
    environment.setdefault("ROUTEOS_DEVELOPMENT_AUTH", "0" if args.production_auth else "1")
    command = [
        str(python),
        "-m",
        "uvicorn",
        "app:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    if args.reload:
        command.append("--reload")

    print(f"RouteOS backend: http://{args.host}:{args.port}")
    print(f"Project root: {ROOT}")
    try:
        return subprocess.run(command, cwd=BACKEND, env=environment).returncode
    except FileNotFoundError:
        print(
            f"Could not import uvicorn with {python}. Install dependencies with:\n"
            f"  {python} -m pip install -r {BACKEND / 'requirements.txt'}",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("\nRouteOS backend stopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
