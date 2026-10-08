"""Exercise the actual Render start command, including database initialization."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


SERVER = Path(__file__).resolve().parents[1] / "serve.py"


def test_render_launcher_binds_port_and_supports_demo_login_from_another_folder(tmp_path):
    with socket.socket() as socket_probe:
        socket_probe.bind(("127.0.0.1", 0))
        port = socket_probe.getsockname()[1]
    environment = {
        **os.environ,
        "PORT": str(port),
        "ROUTEOS_DATABASE": str(tmp_path / "startup.db"),
        "ROUTEOS_DEVELOPMENT_AUTH": "0",
        "ROUTEOS_DEMO_PASSWORD": "Demo123",
    }
    process = subprocess.Popen(
        [sys.executable, "-u", str(SERVER)],
        cwd=tmp_path,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    ready = False
    try:
        deadline = time.monotonic() + 15
        while process.poll() is None and time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(base + "/health", timeout=0.5) as response:
                    ready = response.status == 200
                if ready:
                    break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        if ready:
            for name, role in (("D.B Cooper", "driver"), ("Sukumara Kurup", "driver"), ("Sreekandan Nair", "admin")):
                request = urllib.request.Request(
                    base + "/api/v1/auth/login",
                    data=json.dumps({"name": name, "password": "Demo123"}).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    account = json.load(response)
                assert account["role"] == role
                assert account["auth_token"]
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            output, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=5)
    assert ready, output
    assert "RouteOS: application loaded" in output
    assert "RouteOS: database ready" in output
    assert f"0.0.0.0:{port}" in output


def test_render_launcher_reports_invalid_port_before_loading_application(tmp_path):
    result = subprocess.run(
        [sys.executable, "-u", str(SERVER)],
        cwd=tmp_path,
        env={**os.environ, "PORT": "invalid"},
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode != 0
    assert "RouteOS: starting backend" in result.stdout
    assert "PORT must be a number" in result.stderr
