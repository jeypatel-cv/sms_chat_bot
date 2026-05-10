from __future__ import annotations

import os

from production_app import main


def set_local_defaults() -> None:
    os.environ.setdefault("HOST", "127.0.0.1")
    os.environ.setdefault("PORT", "8000")
    source_configured = os.environ.get("PROPERTIES_SOURCE_URL", "").strip()
    csv_path = os.environ.get("PROPERTIES_CSV_PATH", "").strip()
    if not source_configured:
        if not csv_path or csv_path.endswith("vp_properties_live_export.csv"):
            os.environ["PROPERTIES_CSV_PATH"] = "data/LeasingSnapshot - ChatBotClient.csv"
    os.environ.setdefault("TWILIO_ALLOW_MOCK", "true")
    os.environ.setdefault("TWILIO_VALIDATE_REQUESTS", "false")


if __name__ == "__main__":
    set_local_defaults()
    main()
