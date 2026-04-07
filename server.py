from __future__ import annotations

import os

from production_app import main


def set_local_defaults() -> None:
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", "8000")
    os.environ.setdefault("PROPERTIES_CSV_PATH", "data/vp_properties_live_export.csv")
    os.environ.setdefault("TWILIO_ALLOW_MOCK", "true")
    os.environ.setdefault("TWILIO_VALIDATE_REQUESTS", "false")


if __name__ == "__main__":
    set_local_defaults()
    main()
