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
    with TestClient(routeos_app.app) as client:
        yield client


def auth_headers(user: dict) -> dict:
    return {"X-RouteOS-Token": user["auth_token"]}
