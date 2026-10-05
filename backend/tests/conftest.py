"""
TEST BOOTSTRAP: every backend test imports helpers from here. Before the app
module loads it points ROUTEOS_DATABASE at a throwaway temp file and turns on
ROUTEOS_DEVELOPMENT_AUTH (so tests can log in without real passwords).
"""
import contextlib
import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

os.environ["ROUTEOS_DATABASE"] = str(Path(tempfile.mkdtemp(prefix="routeos-tests-")) / "routeos.db")
os.environ["ROUTEOS_DEVELOPMENT_AUTH"] = "1"

import app as routeos_app  # noqa: E402


@contextlib.contextmanager
def api():
    """Context manager yielding a FastAPI TestClient bound to a fresh app."""
    with TestClient(routeos_app.app) as client:
        yield client


def auth_headers(user: dict) -> dict:
    """Header dict carrying a logged-in user's bearer token."""
    return {"X-RouteOS-Token": user["auth_token"]}
