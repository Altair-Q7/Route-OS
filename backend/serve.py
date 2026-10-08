"""Start the Render backend with visible startup steps and one worker."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import time


def main() -> None:
    print(f"RouteOS: starting backend on Python {sys.version.split()[0]}", flush=True)
    try:
        port = int(os.getenv("PORT", "10000"))
    except ValueError as error:
        raise RuntimeError("PORT must be a number between 1 and 65535") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("PORT must be a number between 1 and 65535")

    # Resolve imports from this script's directory, even when launched elsewhere.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    started = time.monotonic()
    print("RouteOS: loading application", flush=True)
    import uvicorn
    import app

    app.demo_password()
    if not app.DATABASE_PATH.parent.is_dir():
        raise RuntimeError(
            "ROUTEOS_DATABASE directory does not exist. On Render Free, leave "
            "ROUTEOS_DATABASE unset; /var/data requires an attached persistent disk."
        )
    print(f"RouteOS: application loaded in {time.monotonic() - started:.2f}s", flush=True)
    print(f"RouteOS: starting HTTP server on 0.0.0.0:{port}", flush=True)
    uvicorn.run(
        app.app,
        host="0.0.0.0",
        port=port,
        workers=1,
        loop="asyncio",
        http="h11",
        lifespan="on",
        log_level="info",
    )


if __name__ == "__main__":
    main()
