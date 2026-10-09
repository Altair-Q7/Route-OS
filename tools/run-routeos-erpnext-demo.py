#!/usr/bin/env python3
"""Start the local ERPNext connector without saving API secrets to disk.

Run from any directory. Requires the existing ERPNext Docker stack and backend venv.
"""
import argparse
import json
import os
import signal
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", default="erpnext-backend-1")
    parser.add_argument("--site", default="localhost")
    parser.add_argument("--erp-url", default="http://127.0.0.1:8080")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--check", action="store_true", help="Verify ERP API access without starting the backend")
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1] / "backend"
    python = backend / ".venv/bin/python"
    if not python.is_file():
        raise SystemExit("Create backend/.venv and install backend/requirements.txt first.")
    if not 1 <= args.port <= 65535:
        raise SystemExit("Port must be between 1 and 65535")
    result = subprocess.run([
        "docker", "exec", "-i", "-w", "/home/frappe/frappe-bench", args.container,
        "env/bin/python", "-", "--site", args.site, "--apply", "--credentials",
    ], input=(backend / "setup_erpnext.py").read_text(), text=True, capture_output=True)
    if result.returncode:
        # Do not echo stdout: it may contain credentials from a partially completed setup.
        print(result.stderr, file=sys.stderr)
        raise SystemExit("ERPNext setup failed. No RouteOS server was started.")
    try:
        credentials = json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise SystemExit("ERPNext setup did not return integration credentials")
    environment = os.environ.copy()
    environment.update({"PORT": str(args.port), "ROUTEOS_ERPNEXT_URL": args.erp_url,
                        "ROUTEOS_ERPNEXT_API_KEY": credentials["api_key"],
                        "ROUTEOS_ERPNEXT_API_SECRET": credentials["api_secret"]})
    if args.check:
        check = subprocess.run([str(python), "-c",
            "from erpnext_integration import erp_request; "
            "trips=erp_request('GET','/api/resource/Delivery Trip',query={'limit_page_length':1}); "
            "tracking=erp_request('GET','/api/resource/RouteOS Delivery Tracking',query={'limit_page_length':1}); "
            "print('ERPNext authentication, trip read access and tracking schema: OK'); "
            "print('Available trips in check:',len(trips))"], cwd=backend, env=environment)
        raise SystemExit(check.returncode)
    print(f"Local RouteOS + ERPNext backend: http://127.0.0.1:{args.port}", flush=True)
    print("ERP credentials stay in process memory. Press Ctrl+C to stop.", flush=True)
    process = subprocess.Popen([str(python), "-u", str(backend / "serve.py")], env=environment)
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        raise SystemExit(process.wait())
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    main()
