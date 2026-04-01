from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from xml.sax.saxutils import escape


try:
    import google.auth
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
except Exception:  # pragma: no cover - keeps the module importable without deps
    google = None
    Credentials = None
    build = None

try:
    from twilio.request_validator import RequestValidator
    from twilio.rest import Client as TwilioClient
except Exception:  # pragma: no cover - keeps the module importable without deps
    RequestValidator = None
    TwilioClient = None


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_CACHE_TTL_SECONDS = 300
DEFAULT_GOOGLE_SHEET_ID = "1wcw6nsvP4trX28O1l6TdMklLciUXuRvXSYPTnScb_44"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize(text)).strip()


def tokens(text: str) -> set[str]:
    return {token for token in compact(text).split() if token}


def street_line(address: str) -> str:
    return address.split(",")[0]


def format_date(value: str | None) -> str:
    if not value:
        return "not provided"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return value


def parse_number(value: Any) -> float | int | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return value
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    try:
        if "." in cleaned:
            return float(cleaned)
        return int(cleaned)
    except ValueError:
        return None


def truthy_env(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class PropertyRecord:
    property_id: str
    name: str
    address: str
    rent_per_month: float | int | None
    bedrooms: int | None
    bathrooms: int | None
    availability: str
    available_from: str | None
    description: str = ""
    contact_owner: str = ""
    listing_id: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "PropertyRecord":
        return cls(
            property_id=str(row.get("property_id", "")).strip(),
            name=str(row.get("property_name", row.get("name", ""))).strip(),
            address=str(
                row.get(
                    "street_address",
                    row.get("address", ""),
                )
            ).strip(),
            rent_per_month=parse_number(row.get("rent")),
            bedrooms=parse_number(row.get("bedrooms")),
            bathrooms=parse_number(row.get("bathrooms")),
            availability=str(row.get("availability_status", row.get("availability", ""))).strip(),
            available_from=str(row.get("available_from", "")).strip() or None,
            description=str(row.get("description", "")).strip(),
            contact_owner=str(row.get("contact_owner", "")).strip(),
            listing_id=str(row.get("listing_id", "")).strip(),
        )


class PropertyStore:
    def load(self) -> list[PropertyRecord]:
        raise NotImplementedError


class GoogleSheetsPropertyStore(PropertyStore):
    def __init__(
        self,
        sheet_id: str,
        worksheet_name: str,
        credentials_file: str,
        credentials_json: str,
        range_name: str | None = None,
    ):
        self.sheet_id = sheet_id
        self.worksheet_name = worksheet_name
        self.credentials_file = credentials_file
        self.credentials_json = credentials_json
        self.range_name = range_name or f"{worksheet_name}!A:Z"
        self._cached_at: datetime | None = None
        self._cached_records: list[PropertyRecord] = []

    def load(self) -> list[PropertyRecord]:
        ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL_SECONDS)))
        now = datetime.now(timezone.utc)
        if self._cached_at and (now - self._cached_at) < timedelta(seconds=ttl_seconds):
            return self._cached_records

        if Credentials is None or build is None:
            raise RuntimeError(
                "Google Sheets dependencies are not installed. "
                "Install the packages in requirements.txt first."
            )

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        if self.credentials_json:
            credentials = Credentials.from_service_account_info(json.loads(self.credentials_json), scopes=scopes)
        elif self.credentials_file and Path(self.credentials_file).exists():
            credentials = Credentials.from_service_account_file(self.credentials_file, scopes=scopes)
        else:
            if google is None:
                raise RuntimeError("google-auth is not available for default credentials.")
            credentials, _ = google.auth.default(scopes=scopes)
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        response = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=self.sheet_id, range=self.range_name)
            .execute()
        )
        values = response.get("values", [])
        if not values:
            self._cached_records = []
            self._cached_at = now
            return []

        headers = [str(header).strip() for header in values[0]]
        records: list[PropertyRecord] = []
        for row_values in values[1:]:
            row = {headers[i]: row_values[i] if i < len(row_values) else "" for i in range(len(headers))}
            if any(str(value).strip() for value in row.values()):
                records.append(PropertyRecord.from_row(row))

        self._cached_records = records
        self._cached_at = now
        return records


class TwilioMessenger:
    def __init__(self) -> None:
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        self.messaging_service_sid = os.getenv("TWILIO_MESSAGING_SERVICE_SID", "").strip()
        self.allow_mock = truthy_env("TWILIO_ALLOW_MOCK", "true")
        self.client = None

        if self.account_sid and self.auth_token:
            if TwilioClient is None:
                raise RuntimeError("twilio package is not installed. Install requirements.txt first.")
            self.client = TwilioClient(self.account_sid, self.auth_token)

    def send_sms(self, to: str, body: str) -> dict[str, Any]:
        if self.client is None:
            if self.allow_mock:
                return {"sid": None, "status": "mock", "to": to, "body": body}
            raise RuntimeError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are required to send SMS.")

        payload: dict[str, Any] = {"to": to, "body": body}
        if self.messaging_service_sid:
            payload["messaging_service_sid"] = self.messaging_service_sid
        elif self.from_number:
            payload["from_"] = self.from_number
        else:
            raise RuntimeError("Set TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID.")

        message = self.client.messages.create(**payload)
        return {"sid": message.sid, "status": message.status}


class CsvPropertyStore(PropertyStore):
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)

    def load(self) -> list[PropertyRecord]:
        with self.csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return [PropertyRecord.from_row(row) for row in reader]


class ConversationBrain:
    def __init__(self, property_store: PropertyStore):
        self.property_store = property_store
        self.sessions: dict[str, dict[str, Any]] = {}
        self.history: dict[str, list[dict[str, Any]]] = {}

    def get_session(self, phone: str) -> dict[str, Any]:
        if phone not in self.sessions:
            self.sessions[phone] = {
                "property_id": None,
                "human_handoff": False,
                "last_match_type": None,
            }
        return self.sessions[phone]

    def load_properties(self) -> list[PropertyRecord]:
        return self.property_store.load()

    def find_property(self, text: str, session: dict[str, Any]) -> tuple[PropertyRecord | None, str | None]:
        properties = self.load_properties()
        normalized = normalize(text)
        compact_text = compact(text)

        def score_street_match(prop: PropertyRecord) -> tuple[int, str | None]:
            street = street_line(prop.address)
            street_text = compact(street)
            street_tokens = tokens(street)
            input_tokens = tokens(text)
            number_match = re.match(r"^\d+", street_text)
            input_number_match = re.match(r"^\d+", compact_text)
            score = 0

            if street_text and street_text in compact_text:
                return 100, "exact"
            if prop.address.lower() in normalized:
                return 100, "exact"
            if prop.property_id.lower() in normalized or prop.name.lower() in normalized:
                return 100, "exact"
            if prop.listing_id and prop.listing_id.lower() in normalized:
                return 100, "exact"

            overlap = street_tokens & input_tokens
            if overlap:
                score += len(overlap) * 20
            if number_match and input_number_match and number_match.group(0) == input_number_match.group(0):
                score += 40
            if street_tokens and input_tokens and (street_tokens <= input_tokens or input_tokens <= street_tokens):
                score += 25

            if score >= 40:
                return score, "partial"
            return 0, None

        best_prop: PropertyRecord | None = None
        best_score = 0
        best_match_type: str | None = None

        for prop in properties:
            candidates = [
                prop.property_id.lower(),
                prop.address.lower(),
                street_line(prop.address).lower(),
                prop.name.lower(),
                prop.listing_id.lower() if prop.listing_id else "",
            ]
            if any(candidate and candidate in normalized for candidate in candidates):
                session["property_id"] = prop.property_id
                session["last_match_type"] = "exact"
                return prop, "exact"

            score, match_type = score_street_match(prop)
            if score > best_score:
                best_score = score
                best_prop = prop
                best_match_type = match_type

        if best_prop is not None and best_match_type is not None:
            session["property_id"] = best_prop.property_id
            session["last_match_type"] = best_match_type
            return best_prop, best_match_type

        property_id = session.get("property_id")
        if property_id:
            for prop in properties:
                if prop.property_id == property_id:
                    return prop, "session"

        session["last_match_type"] = None
        return None, None

    def answer_property_question(self, prop: PropertyRecord, normalized: str) -> str:
        rent = f"${int(prop.rent_per_month):,}" if prop.rent_per_month is not None else "not provided"
        bedrooms = prop.bedrooms if prop.bedrooms is not None else "not provided"
        bathrooms = prop.bathrooms if prop.bathrooms is not None else "not provided"
        rooms = f"{bedrooms} bedrooms, {bathrooms} bathrooms"
        available_from = format_date(prop.available_from)
        availability = prop.availability or "unknown"

        if any(word in normalized for word in ["available from", "move in", "move-in", "when available"]):
            return f"{prop.name} is available from {available_from}."
        if any(word in normalized for word in ["rent", "price", "cost", "how much"]):
            return f"The rent for {prop.name} is {rent} per month."
        if any(word in normalized for word in ["bedroom", "bathroom", "rooms", "bed", "bath"]):
            return f"{prop.name} has {rooms}."
        if any(word in normalized for word in ["available", "availability", "still active", "vacant"]):
            return f"Yes, {prop.name} is currently {availability}."
        if any(word in normalized for word in ["more details", "details", "info", "information"]):
            return (
                f"{prop.name} at {prop.address} is {availability}, "
                f"{rooms}, rent {rent} per month, and available from {available_from}."
            )

        return (
            f"{prop.name} at {prop.address} is {availability}. "
            f"It has {rooms} and rent is {rent} per month."
        )

    def respond(self, phone: str, text: str) -> dict[str, Any]:
        session = self.get_session(phone)
        prop, match_type = self.find_property(text, session)
        normalized = normalize(text)
        reply = ""
        intent = "unknown"

        if session.get("human_handoff"):
            reply = "A leasing specialist has been notified. Please hold while we review your request."
            intent = "handoff"
        elif any(word in normalized for word in ["human", "agent", "person", "call me"]):
            session["human_handoff"] = True
            reply = (
                "No problem. I can connect you with a leasing specialist. "
                "Please share the property address or listing ID if you have it."
            )
            intent = "human_handoff"
        elif prop is None:
            reply = (
                "Please send the property address or listing ID, "
                "and I can check availability, rent, and bedroom details."
            )
            intent = "clarify_property"
        elif match_type == "partial":
            reply = (
                f"I found {prop.name} at {prop.address}. "
                "Do you want rent, availability, or bedroom details for this property?"
            )
            intent = "property_suggestion"
        else:
            intent = "property_qna"
            reply = self.answer_property_question(prop, normalized)

        message = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "phone": phone,
            "incoming": text,
            "reply": reply,
            "intent": intent,
            "property_id": prop.property_id if prop else session.get("property_id"),
        }
        self.history.setdefault(phone, []).append(message)
        return message


class TwilioWebhookSecurity:
    def __init__(self) -> None:
        self.validator = None
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.enabled = truthy_env("TWILIO_VALIDATE_REQUESTS", "true") and bool(auth_token)
        if self.enabled:
            if RequestValidator is None:
                raise RuntimeError("twilio package is not installed. Install requirements.txt first.")
            self.validator = RequestValidator(auth_token)

    def validate(self, url: str, params: dict[str, str], signature: str) -> bool:
        if not self.enabled:
            return True
        if self.validator is None:
            return False
        return bool(self.validator.validate(url, params, signature))

    def external_url(self, request_path: str, headers: dict[str, str]) -> str:
        base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
        if base_url:
            return f"{base_url}{request_path}"

        proto = headers.get("X-Forwarded-Proto") or "https"
        host = headers.get("X-Forwarded-Host") or headers.get("Host") or "localhost"
        return f"{proto}://{host}{request_path}"


class ProductionRequestHandler(BaseHTTPRequestHandler):
    brain: ConversationBrain | None = None
    messenger: TwilioMessenger | None = None
    security: TwilioWebhookSecurity | None = None

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, body_text: str, status: int = 200, content_type: str = "text/plain; charset=utf-8") -> None:
        body = body_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_xml(self, body_text: str, status: int = 200) -> None:
        body = body_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            return self._send_text("ok")
        if parsed.path == "/":
            return self._send_text(
                """<html>
  <head>
    <title>VP Realty SMS Pilot</title>
    <meta charset="utf-8" />
    <style>
      body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.5; }
      code { background: #f2f2f2; padding: 2px 6px; border-radius: 4px; }
      a { color: #0b66ff; }
    </style>
  </head>
  <body>
    <h1>VP Realty SMS Pilot</h1>
    <p>The service is running.</p>
    <ul>
      <li><a href="/healthz">/healthz</a></li>
      <li><a href="/demo">/demo</a></li>
      <li><code>/twilio/sms</code> for inbound SMS webhooks</li>
    </ul>
  </body>
</html>""",
                content_type="text/html; charset=utf-8",
            )
        if parsed.path == "/demo":
            path = STATIC_DIR / "index.html"
            if not path.exists() or not path.is_file():
                return self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path == "/api/properties":
            return self._send_json({"properties": [asdict(prop) for prop in self.brain.load_properties()]})
        if parsed.path == "/demo/history":
            phone = self._query_param("phone")
            return self._send_json({"history": self.brain.history.get(phone, [])})
        if parsed.path == "/api/history":
            phone = self._query_param("phone")
            return self._send_json({"history": self.brain.history.get(phone, [])})
        if parsed.path.startswith("/static/"):
            rel = parsed.path.removeprefix("/static/")
            path = STATIC_DIR / rel
            if not path.exists() or not path.is_file():
                return self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/twilio/sms":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            form = parse_qs(raw)
            phone = (form.get("From", [""]) or [""])[0].strip()
            text = (form.get("Body", [""]) or [""])[0].strip()
            if not phone or not text:
                return self._send_xml(self._twiml("Missing phone number or message."), status=400)

            request_params = {key: values[0] for key, values in form.items()}
            request_url = self.security.external_url(self.path, dict(self.headers))
            signature = self.headers.get("X-Twilio-Signature", "")
            if not self.security.validate(request_url, request_params, signature):
                return self._send_xml(self._twiml("Forbidden"), status=403)

            result = self.brain.respond(phone, text)
            try:
                outbound = self.messenger.send_sms(phone, result["reply"])
            except Exception as exc:
                return self._send_xml(self._twiml(f"Twilio send failed: {exc}"), status=500)

            result["twilio"] = outbound
            return self._send_xml(self._twiml(""))

        if parsed.path in {"/demo/message", "/api/message"}:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return self._send_json({"error": "Invalid JSON"}, status=400)

            phone = str(data.get("phone", "")).strip()
            text = str(data.get("text", "")).strip()
            if not phone or not text:
                return self._send_json({"error": "phone and text are required"}, status=400)
            result = self.brain.respond(phone, text)
            return self._send_json(result)

        if parsed.path in {"/demo/reset", "/api/reset"}:
            phone = self._query_param("phone")
            if phone:
                self.brain.sessions.pop(phone, None)
                self.brain.history.pop(phone, None)
            else:
                self.brain.sessions.clear()
                self.brain.history.clear()
            return self._send_json({"ok": True})

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args) -> None:
        return

    def _query_param(self, name: str) -> str:
        parsed = urlparse(self.path)
        return parse_qs(parsed.query).get(name, [""])[0]

    def _twiml(self, message: str) -> str:
        return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(message)}</Message></Response>'


def build_store_from_env() -> PropertyStore:
    csv_path = os.getenv("PROPERTIES_CSV_PATH", "").strip()
    if csv_path:
        return CsvPropertyStore(csv_path)

    sheet_id = os.getenv("GOOGLE_SHEET_ID", DEFAULT_GOOGLE_SHEET_ID).strip()
    worksheet_name = os.getenv("GOOGLE_SHEET_TAB", "Properties").strip()
    credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()

    if sheet_id:
        return GoogleSheetsPropertyStore(sheet_id, worksheet_name, credentials_file, credentials_json)

    raise RuntimeError(
        "Set GOOGLE_SHEET_ID + GOOGLE_APPLICATION_CREDENTIALS for Google Sheets, "
        "or PROPERTIES_CSV_PATH for a local CSV fallback."
    )


def build_brain_and_services() -> tuple[ConversationBrain, TwilioMessenger, TwilioWebhookSecurity]:
    store = build_store_from_env()
    brain = ConversationBrain(store)
    messenger = TwilioMessenger()
    security = TwilioWebhookSecurity()
    return brain, messenger, security


def main() -> None:
    parser = argparse.ArgumentParser(description="VP Realty production SMS backend")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", default=int(os.getenv("PORT", "8000")), type=int)
    args = parser.parse_args()

    handler_cls = ProductionRequestHandler
    brain, messenger, security = build_brain_and_services()
    handler_cls.brain = brain
    handler_cls.messenger = messenger
    handler_cls.security = security
    server = ThreadingHTTPServer((args.host, args.port), handler_cls)
    print(f"VP Realty production backend running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
