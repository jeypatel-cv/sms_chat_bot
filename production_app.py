from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import re
from difflib import SequenceMatcher
from io import StringIO
from dataclasses import dataclass
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
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
DEFAULT_GOOGLE_SHEET_ID = "18b9gxA8GoC_-cpmjr-nG9ze2wG5NAfWWxhlg5MCfM7k"
DEFAULT_HANDOFF_TTL_SECONDS = 900
APP_VERSION = "1.1"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize(text)).strip()


def tokens(text: str) -> set[str]:
    return {token for token in compact(text).split() if token}


def street_line(address: str) -> str:
    return address.split(",")[0]


def canonical_header(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize(name)).strip("_")


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


PROPERTY_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "property_id": ("property_id", "id"),
    "name": ("property_name", "name", "property", "property_title"),
    "address": ("street_address", "address", "full_address", "property_address", "location"),
    "city": ("city", "town"),
    "rent_per_month": (
        "rent",
        "rent_per_month",
        "monthly_rent",
        "price",
        "advertised_rent",
        "schd_rent",
        "new_rent",
        "computed_market_rent",
    ),
    "bedrooms": ("bedrooms", "beds", "bed"),
    "bathrooms": ("bathrooms", "baths", "bath"),
    "bed_and_bath": ("bed_and_bath", "beds_baths", "bedbath"),
    "availability": ("availability_status", "availability", "status", "unit_status", "rent_ready"),
    "available_from": (
        "available_from",
        "availability_date",
        "available_on",
        "next_move_in",
        "ready_for_showing_on",
        "available date",
        "move_in_date",
        "move in date",
    ),
    "description": ("description", "summary", "remarks", "notes"),
    "manager_name": ("manager_name", "manager", "leasing_agent", "contact_name"),
    "manager_email": ("manager_email", "manager email", "email", "contact_email"),
    "manager_phone": ("manager_phone", "contact_phone", "phone", "manager phone"),
    "contact_owner": ("contact_owner", "leasing_owner", "owner_email"),
    "contact_info": ("contact", "contact_info", "leasing_contact"),
}


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        normalized[canonical_header(str(key))] = value
    return normalized


def first_row_value(row: dict[str, Any], *candidates: str) -> Any:
    for candidate in candidates:
        value = row.get(canonical_header(candidate))
        if value not in (None, ""):
            return value
    return ""


def coerce_text(value: Any) -> str:
    return str(value).strip()


def coerce_optional_text(value: Any) -> str | None:
    text = coerce_text(value)
    return text or None


def parse_contact_info(value: Any) -> tuple[str, str, str]:
    text = coerce_text(value)
    if not text:
        return "", "", ""

    chunks = [chunk.strip() for chunk in re.split(r"\s*:\s*", text) if chunk.strip()]
    if not chunks:
        return "", "", ""

    name = chunks[0]
    email = ""
    phone = ""
    for chunk in chunks[1:]:
        if not email and "@" in chunk:
            email = chunk
            continue
        if not phone:
            phone = chunk
            continue
        if not name:
            name = chunk

    if not email:
        email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        if email_match:
            email = email_match.group(0)

    if not phone:
        phone_match = re.search(r"(\(?\+?\d[\d\s().-]{7,}\d\)?)", text)
        if phone_match:
            phone = phone_match.group(1).strip()

    if not name and text:
        name = text.split(":")[0].strip()

    return name, email, phone


def parse_bed_and_bath(value: Any) -> tuple[int | None, int | None]:
    text = coerce_text(value)
    if not text:
        return None, None

    match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
    if match:
        return parse_number(match.group(1)), parse_number(match.group(2))

    numbers = [parse_number(part) for part in re.findall(r"\d+(?:\.\d+)?", text)]
    numbers = [number for number in numbers if number is not None]
    if len(numbers) >= 2:
        return numbers[0], numbers[1]
    if len(numbers) == 1:
        return numbers[0], None
    return None, None


def join_nonempty(*parts: Any, separator: str = " ") -> str:
    return separator.join(part.strip() for part in map(coerce_text, parts) if part.strip())


def build_google_credentials(scopes: list[str], credentials_file: str, credentials_json: str):
    if Credentials is None or build is None:
        raise RuntimeError(
            "Google Sheets dependencies are not installed. "
            "Install the packages in requirements.txt first."
        )
    if credentials_json:
        return Credentials.from_service_account_info(json.loads(credentials_json), scopes=scopes)
    if credentials_file and Path(credentials_file).exists():
        return Credentials.from_service_account_file(credentials_file, scopes=scopes)
    if google is None:
        raise RuntimeError("google-auth is not available for default credentials.")
    credentials, _ = google.auth.default(scopes=scopes)
    return credentials


@dataclass
class PropertyRecord:
    property_id: str
    name: str
    address: str
    city: str
    rent_per_month: float | int | None
    bedrooms: int | None
    bathrooms: int | None
    availability: str
    available_from: str | None
    description: str = ""
    manager_name: str = ""
    manager_email: str = ""
    manager_phone: str = ""
    contact_owner: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "PropertyRecord":
        normalized_row = normalize_row(row)
        property_id = coerce_text(
            first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["property_id"])
        )
        name = coerce_text(first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["name"]))
        address = coerce_text(first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["address"]))
        city = coerce_text(first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["city"]))
        street = coerce_text(first_row_value(normalized_row, "street"))
        street2 = coerce_text(first_row_value(normalized_row, "street2"))
        state = coerce_text(first_row_value(normalized_row, "state"))
        zip_code = coerce_text(first_row_value(normalized_row, "zip"))
        if not city and address and "," in address:
            address_parts = [part.strip() for part in address.split(",") if part.strip()]
            if len(address_parts) >= 2:
                city = address_parts[1]
        if not address and street:
            address = join_nonempty(street, street2, city, state, zip_code, separator=", ")
        if not address and name:
            address = name
        if not name and address:
            name = street_line(address)
        combined_contact_name, combined_contact_email, combined_contact_phone = parse_contact_info(
            first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["contact_info"])
        )
        manager_name = coerce_text(
            first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["manager_name"])
            or combined_contact_name
            or first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["contact_owner"])
        )
        manager_email = coerce_text(
            first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["manager_email"])
            or combined_contact_email
            or first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["contact_owner"])
        )
        manager_phone = coerce_text(
            first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["manager_phone"])
            or combined_contact_phone
        )
        contact_owner = coerce_text(
            first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["contact_owner"])
            or combined_contact_email
        )
        bed_and_bath = first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["bed_and_bath"])
        bedrooms = parse_number(first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["bedrooms"]))
        bathrooms = parse_number(first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["bathrooms"]))
        if bedrooms is None and bathrooms is None:
            bedrooms, bathrooms = parse_bed_and_bath(bed_and_bath)
        return cls(
            property_id=property_id,
            name=name,
            address=address,
            city=city,
            rent_per_month=parse_number(first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["rent_per_month"])),
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            availability=coerce_text(first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["availability"])),
            available_from=coerce_optional_text(
                first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["available_from"])
            ),
            description=coerce_text(first_row_value(normalized_row, *PROPERTY_FIELD_ALIASES["description"])),
            manager_name=manager_name,
            manager_email=manager_email,
            manager_phone=manager_phone,
            contact_owner=contact_owner,
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
        self.range_name = range_name or f"{worksheet_name}!A:AZ"
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
        credentials = build_google_credentials(scopes, self.credentials_file, self.credentials_json)
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


@dataclass
class MessageLogRecord:
    timestamp: str
    direction: str
    from_number: str
    to_number: str
    message_text: str
    property_id: str = ""
    intent: str = ""
    status: str = ""
    error: str = ""


class MessageLogger:
    def log(self, record: MessageLogRecord) -> dict[str, Any]:
        raise NotImplementedError


class NoopMessageLogger(MessageLogger):
    def log(self, record: MessageLogRecord) -> dict[str, Any]:
        return {"status": "noop"}


class ConsoleMessageLogger(MessageLogger):
    def log(self, record: MessageLogRecord) -> dict[str, Any]:
        print(
            " | ".join(
                [
                    f"[{record.timestamp}]",
                    record.direction,
                    f"from={record.from_number}",
                    f"to={record.to_number}",
                    f"status={record.status}",
                    f"intent={record.intent}",
                    f"property_id={record.property_id or '-'}",
                    f"text={record.message_text}",
                    f"error={record.error or '-'}",
                ]
            ),
            flush=True,
        )
        return {"status": "printed"}


class CompositeMessageLogger(MessageLogger):
    def __init__(self, loggers: list[MessageLogger]):
        self.loggers = loggers

    def log(self, record: MessageLogRecord) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for logger in self.loggers:
            try:
                results.append(logger.log(record))
            except Exception as exc:
                results.append({"status": "error", "error": str(exc)})
        return {"status": "composite", "results": results}


class JsonlMessageLogger(MessageLogger):
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: MessageLogRecord) -> dict[str, Any]:
        payload = json.dumps(asdict(record), ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(payload + "\n")
        return {"status": "written", "path": str(self.path)}


class GoogleSheetsMessageLogger(MessageLogger):
    def __init__(
        self,
        sheet_id: str,
        worksheet_name: str,
        credentials_file: str,
        credentials_json: str,
    ):
        self.sheet_id = sheet_id
        self.worksheet_name = worksheet_name
        self.credentials_file = credentials_file
        self.credentials_json = credentials_json
        self.range_name = f"{worksheet_name}!A:I"

    def log(self, record: MessageLogRecord) -> dict[str, Any]:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = build_google_credentials(scopes, self.credentials_file, self.credentials_json)
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        row = [
            record.timestamp,
            record.direction,
            record.from_number,
            record.to_number,
            record.message_text,
            record.property_id,
            record.intent,
            record.status,
            record.error,
        ]
        response = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self.sheet_id,
                range=self.range_name,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            )
            .execute()
        )
        return {"status": "written", "updates": response.get("updates", {})}


class AppsScriptMessageLogger(MessageLogger):
    def __init__(self, web_app_url: str, secret: str):
        self.web_app_url = web_app_url
        self.secret = secret

    def log(self, record: MessageLogRecord) -> dict[str, Any]:
        if not self.web_app_url:
            raise RuntimeError("MESSAGE_LOG_APPS_SCRIPT_URL is required.")
        if not self.secret:
            raise RuntimeError("MESSAGE_LOG_APPS_SCRIPT_SECRET is required.")

        payload = asdict(record)
        payload["secret"] = self.secret
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self.web_app_url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8", errors="replace").strip()

        if response_body:
            try:
                parsed = json.loads(response_body)
            except json.JSONDecodeError:
                parsed = {"raw": response_body}
        else:
            parsed = {}

        return {"status": "written", "response": parsed}


class CsvPropertyStore(PropertyStore):
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)

    def load(self) -> list[PropertyRecord]:
        with self.csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return [PropertyRecord.from_row(row) for row in reader]


class FallbackPropertyStore(PropertyStore):
    def __init__(self, primary: PropertyStore, fallback: PropertyStore):
        self.primary = primary
        self.fallback = fallback

    def load(self) -> list[PropertyRecord]:
        try:
            return self.primary.load()
        except Exception:
            return self.fallback.load()


class RemotePropertyStore(PropertyStore):
    def __init__(self, source_url: str, source_format: str = ""):
        self.source_url = source_url
        self.source_format = source_format.strip().lower()

    def load(self) -> list[PropertyRecord]:
        request = Request(self.source_url, headers={"User-Agent": "VP-Realty-SMS-Pilot/1.0"})
        with urlopen(request, timeout=20) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            raw = response.read().decode("utf-8", errors="replace")

        format_hint = self.source_format
        if not format_hint:
            if "json" in content_type:
                format_hint = "json"
            elif "csv" in content_type or "text/plain" in content_type:
                format_hint = "csv"
            elif raw.lstrip().startswith("{") or raw.lstrip().startswith("["):
                format_hint = "json"
            elif "," in raw.splitlines()[0] if raw.splitlines() else False:
                format_hint = "csv"

        if format_hint == "csv":
            reader = csv.DictReader(StringIO(raw))
            return [PropertyRecord.from_row(row) for row in reader]

        if format_hint == "json":
            payload = json.loads(raw)
            if isinstance(payload, dict):
                rows = payload.get("properties", payload.get("rows", payload.get("data", [])))
            else:
                rows = payload
            if not isinstance(rows, list):
                raise RuntimeError("Remote JSON source must be a list or contain a properties/data/rows list.")
            return [PropertyRecord.from_row(row) for row in rows if isinstance(row, dict)]

        raise RuntimeError(
            "Remote properties source must return CSV or JSON. "
            "The provided URL appears to be an HTML page or unsupported format."
        )


class ConversationBrain:
    def __init__(self, property_store: PropertyStore):
        self.property_store = property_store
        self.sessions: dict[str, dict[str, Any]] = {}
        self.history: dict[str, list[dict[str, Any]]] = {}
        self.max_list_results = 3

    def get_session(self, phone: str) -> dict[str, Any]:
        if phone not in self.sessions:
            self.sessions[phone] = {
                "property_id": None,
                "human_handoff": False,
                "human_handoff_until": None,
                "last_match_type": None,
            }
        return self.sessions[phone]

    def _handoff_is_active(self, session: dict[str, Any]) -> bool:
        until = session.get("human_handoff_until")
        if not until:
            return False
        try:
            expires_at = datetime.fromisoformat(str(until))
        except ValueError:
            session["human_handoff"] = False
            session["human_handoff_until"] = None
            return False
        if datetime.now(timezone.utc) >= expires_at:
            session["human_handoff"] = False
            session["human_handoff_until"] = None
            return False
        return True

    def _session_property(self, session: dict[str, Any], properties: list[PropertyRecord]) -> PropertyRecord | None:
        property_id = coerce_text(session.get("property_id"))
        if not property_id:
            return None
        for prop in properties:
            if coerce_text(prop.property_id) == property_id:
                return prop
        return None

    def _looks_like_address_query(self, text: str) -> bool:
        normalized = normalize(text)
        compact_text = compact(text)
        if self.looks_like_new_property_reference(text):
            return True
        if re.search(r"\b\d+\b", text) and any(term in normalized for term in {"address", "listing", "home", "house", "unit"}):
            return True
        if re.search(
            r"\b\d+\s+[a-z0-9]+\s+(?:st|street|rd|road|dr|drive|ln|lane|ave|avenue|blvd|boulevard|ct|court|cir|circle|trl|trail|way|pkwy|parkway|hwy|highway|loop)\b",
            compact_text,
        ):
            return True
        return False

    def load_properties(self) -> list[PropertyRecord]:
        return self.property_store.load()

    def extract_budget_limit(self, text: str) -> float | int | None:
        normalized = normalize(text)
        patterns = [
            r"(?:max|maximum|budget|under|below|less than|up to|upto|no more than)\s*(?:is|of|at|around|about)?\s*\$?\s*(\d[\d,]*(?:\.\d+)?)",
            r"\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:max|maximum|budget|or less|under|below|less than|up to|upto)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return parse_number(match.group(1))

        budget_terms = ["budget", "max", "maximum", "under", "below", "less than", "up to", "upto", "or less"]
        if any(word in normalized for word in budget_terms):
            bare_match = re.search(r"\$?\s*(\d[\d,]*(?:\.\d+)?)", normalized)
            if bare_match:
                return parse_number(bare_match.group(1))

        return None

    def _city_match_score(self, city: str, text: str) -> float:
        city_norm = normalize(city)
        city_compact = compact(city)
        if not city_norm or not city_compact:
            return 0.0

        normalized = normalize(text)
        compact_text = compact(text)
        text_tokens = tokens(text)
        city_tokens = tokens(city)

        if city_norm in normalized or city_compact in compact_text:
            return 1.0
        if city_tokens and city_tokens <= text_tokens:
            return 0.97
        if not text_tokens:
            return 0.0

        phrase_score = SequenceMatcher(None, city_compact, compact_text).ratio()
        token_scores = []
        for city_token in city_tokens or {city_compact}:
            best_ratio = 0.0
            for text_token in text_tokens:
                best_ratio = max(best_ratio, SequenceMatcher(None, city_token, text_token).ratio())
            token_scores.append(best_ratio)

        token_score = sum(token_scores) / len(token_scores) if token_scores else 0.0
        return max(phrase_score, token_score)

    def detect_city(self, text: str, properties: list[PropertyRecord]) -> str | None:
        cities = []
        for prop in properties:
            city = prop.city.strip()
            if city and city not in cities:
                cities.append(city)
        cities.sort(key=lambda value: len(compact(value)), reverse=True)

        best_city = None
        best_score = 0.0
        for city in cities:
            city_norm = normalize(city)
            city_compact = compact(city)
            city_tokens = tokens(city)
            normalized = normalize(text)
            compact_text = compact(text)
            if city_norm and city_norm in normalized:
                return city
            if city_compact and city_compact in compact_text:
                return city
            if city_tokens and city_tokens <= tokens(text):
                return city

            score = self._city_match_score(city, text)
            if score > best_score:
                best_city = city
                best_score = score

        if best_city is not None and best_score >= 0.78:
            return best_city
        return None

    def list_properties_reply(self, properties: list[PropertyRecord], label: str, max_results: int | None = None) -> str:
        if not properties:
            return f"I could not find any properties in {label}."

        limit = max_results or self.max_list_results
        limited = properties[:limit]
        label_text = f"{label} options" if not label.startswith("$") else f"Under {label} options"
        items = []
        for prop in limited:
            rent = f"${int(prop.rent_per_month):,}" if prop.rent_per_month is not None else "not provided"
            items.append(f"{prop.address} - {rent}")
        reply = f"{label_text}: " + "; ".join(items)
        if len(properties) > limit:
            reply += (
                f". And {len(properties) - limit} more. "
                + ("Send the address to get details." if label.startswith("$") else "Send your budget or the address to narrow it down.")
            )
        else:
            reply += " " + ("Send the address to get details." if label.startswith("$") else "Send your budget or the address to narrow it down.")
        return reply

    def find_city_matches(self, text: str, properties: list[PropertyRecord]) -> tuple[str | None, list[PropertyRecord]]:
        city = self.detect_city(text, properties)
        if not city:
            return None, []
        matches = [prop for prop in properties if normalize(prop.city) == normalize(city)]
        matches.sort(key=lambda prop: (prop.rent_per_month is None, prop.rent_per_month or 0, prop.name))
        return city, matches

    def find_budget_matches(self, text: str, properties: list[PropertyRecord]) -> tuple[float | int | None, list[PropertyRecord]]:
        budget = self.extract_budget_limit(text)
        if budget is None:
            return None, []
        matches = [prop for prop in properties if prop.rent_per_month is not None and prop.rent_per_month <= budget]
        matches.sort(key=lambda prop: (prop.rent_per_month is None, prop.rent_per_month or 0, prop.name))
        return budget, matches

    def looks_like_new_property_reference(self, text: str) -> bool:
        normalized = normalize(text)
        compact_text = compact(text)
        street_terms = {
            "street",
            "st",
            "road",
            "rd",
            "lane",
            "ln",
            "drive",
            "dr",
            "boulevard",
            "blvd",
            "court",
            "ct",
            "place",
            "pl",
            "parkway",
            "pkwy",
            "trail",
            "trl",
            "way",
            "wy",
            "circle",
            "cir",
            "avenue",
            "ave",
        }
        street_pattern = r"\b\d+\s+(?:[a-z0-9]+\s+){0,4}(?:" + "|".join(street_terms) + r")\b"
        if re.search(street_pattern, normalized):
            return True
        if re.search(r"\b(?:apt|apartment|suite|unit)\s*\d+\b", normalized):
            return True
        return any(term in normalized.split() for term in street_terms) or any(term in compact_text.split() for term in street_terms)

    def looks_like_explicit_property_reference(self, text: str) -> bool:
        normalized = normalize(text)
        if self.looks_like_new_property_reference(text):
            return True

        property_terms = {
            "apartment",
            "apartments",
            "home",
            "homes",
            "house",
            "houses",
            "townhome",
            "townhomes",
            "condo",
            "condos",
            "community",
            "residence",
            "residences",
            "village",
            "villages",
            "villa",
            "villas",
            "estate",
            "estates",
            "flats",
            "lofts",
        }
        if any(term in normalized.split() for term in property_terms):
            return True
        if re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4}\b", text):
            return True
        return False

    def looks_like_followup_question(self, text: str) -> bool:
        normalized = normalize(text)
        words = normalized.split()
        if not words:
            return False
        if self.looks_like_explicit_property_reference(text):
            return False

        followup_phrases = [
            "how many",
            "how much",
            "what is",
            "what's",
            "when is",
            "is it",
            "does this property have",
            "available",
            "rent",
            "price",
            "cost",
            "fee",
            "bed",
            "bath",
            "details",
            "info",
            "information",
            "move in",
            "move-in",
        ]
        if len(words) <= 12 and any(phrase in normalized for phrase in followup_phrases):
            return True
        if len(words) <= 4 and any(word in words for word in {"it", "this", "that", "there"}):
            return True
        return False

    def find_property(
        self,
        text: str,
        session: dict[str, Any],
        properties: list[PropertyRecord] | None = None,
    ) -> tuple[PropertyRecord | None, str | None]:
        properties = properties or self.load_properties()
        normalized = normalize(text)
        compact_text = compact(text)
        address_like_query = self._looks_like_address_query(text)
        city_hint = self.detect_city(text, properties)
        tokens_count = len(tokens(text))
        area_only_query = bool(city_hint) and tokens_count <= 3 and not any(ch.isdigit() for ch in text)

        if area_only_query:
            session["last_match_type"] = None
            return None, None

        def score_street_match(prop: PropertyRecord) -> tuple[int, str | None]:
            street = street_line(prop.address)
            street_text = compact(street)
            street_tokens = tokens(street)
            input_tokens = tokens(text)
            number_match = re.match(r"^\d+", street_text)
            input_number_match = re.search(r"\b\d+\b", compact_text)
            score = 0
            street_ratio = SequenceMatcher(None, street_text, compact_text).ratio() if street_text and compact_text else 0.0

            if street_text and street_text in compact_text:
                return 100, "exact"
            if prop.address.lower() in normalized:
                return 100, "exact"
            if prop.property_id.lower() in normalized or prop.name.lower() in normalized:
                return 100, "exact"
            overlap = street_tokens & input_tokens
            if overlap:
                score += len(overlap) * 20
            if number_match and input_number_match and number_match.group(0) == input_number_match.group(0):
                score += 35
            elif number_match and input_number_match and number_match.group(0) != input_number_match.group(0):
                score -= 20
            if street_tokens and input_tokens and (street_tokens <= input_tokens or input_tokens <= street_tokens):
                score += 20
            if street_ratio >= 0.9:
                score += 30
            elif street_ratio >= 0.84 and overlap:
                score += 15
            elif street_ratio >= 0.8 and len(overlap) >= 2:
                score += 10
            if prop.city and normalize(prop.city) in normalized:
                score += 6
            address_zip = re.search(r"\b\d{5}\b", prop.address)
            if address_zip and address_zip.group(0) in normalized:
                score += 6

            partial_threshold = 45 if address_like_query or any(term in normalized for term in {"code", "entry code", "access code", "gate code", "lock code", "door code"}) else 55
            if score >= partial_threshold:
                return score, "partial"
            return 0, None

        best_prop: PropertyRecord | None = None
        best_score = 0
        best_match_type: str | None = None

        for prop in properties:
            property_id_text = prop.property_id.lower()
            candidates = [
                prop.address.lower(),
                street_line(prop.address).lower(),
                prop.name.lower(),
            ]
            if property_id_text and re.search(rf"\b{re.escape(property_id_text)}\b", normalized):
                session["property_id"] = prop.property_id
                session["last_match_type"] = "exact"
                return prop, "exact"
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

        if address_like_query:
            session["last_match_type"] = None
            return None, "address_like"

        property_id = session.get("property_id")
        if property_id:
            if self.looks_like_explicit_property_reference(text):
                session["last_match_type"] = None
                return None, None
            if not self.looks_like_followup_question(text):
                session["last_match_type"] = None
                return None, None
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
        if any(word in normalized for word in ["code", "entry code", "access code", "gate code", "lock code", "door code"]):
            manager_phone = prop.manager_phone.strip()
            if manager_phone:
                return (
                    f"The entry code is 1975. If that does not work, please contact the property manager at {manager_phone}."
                )
            return "The entry code is 1975. If that does not work, please contact the leasing team at 972-591-8075."
        if any(word in normalized for word in ["contact", "manager", "phone", "email", "number"]):
            return self.contact_details_for_property(prop)
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
            f"For more details about {prop.name}, please contact the leasing team."
        )

    def property_summary(self, prop: PropertyRecord) -> str:
        rent = f"${int(prop.rent_per_month):,}" if prop.rent_per_month is not None else "not provided"
        bedrooms = prop.bedrooms if prop.bedrooms is not None else "not provided"
        bathrooms = prop.bathrooms if prop.bathrooms is not None else "not provided"
        availability = prop.availability or "unknown"
        available_from = format_date(prop.available_from)
        return (
            f"{prop.name} at {prop.address} is {availability}. "
            f"It has {bedrooms} bedrooms, {bathrooms} bathrooms, rent {rent} per month, "
            f"and is available from {available_from}."
        )

    def footer_for_property(self, prop: PropertyRecord | None) -> str:
        if prop is None:
            return "For more details, call the leasing team at 972-591-8075."

        manager_phone = prop.manager_phone.strip()
        if manager_phone:
            return f"For more details, call {manager_phone}."
        return "For more details, call the leasing team at 972-591-8075."

    def contact_details_for_property(self, prop: PropertyRecord | None) -> str:
        if prop is None:
            return "For more details, call the leasing team at 972-591-8075."

        manager_phone = prop.manager_phone.strip()
        manager_email = prop.manager_email.strip()
        if manager_phone and manager_email:
            return f"For more details, call {manager_phone} or email {manager_email}."
        if manager_phone:
            return f"For more details, call {manager_phone}."
        if manager_email:
            return f"For more details, email {manager_email}."
        return "For more details, call the leasing team at 972-591-8075."

    def add_footer(self, reply: str, prop: PropertyRecord | None) -> str:
        normalized_reply = normalize(reply)
        if normalized_reply.startswith("the entry code is 1975"):
            return reply
        if normalized_reply.startswith("for more details"):
            return reply
        footer = self.footer_for_property(prop)
        if not footer:
            return reply
        if footer.lower() in normalized_reply:
            return reply
        return f"{reply} {footer}"

    def respond(self, phone: str, text: str) -> dict[str, Any]:
        session = self.get_session(phone)
        self._handoff_is_active(session)
        properties = self.load_properties()
        normalized = normalize(text)
        budget_limit = self.extract_budget_limit(text)
        detail_terms = ("bedroom", "bathroom", "bedrooms", "bathrooms", "bed", "bath", "how many")
        code_terms = ("code", "entry code", "access code", "gate code", "lock code", "door code")
        property_info_terms = (
            "available from",
            "move in",
            "move-in",
            "when available",
            "rent",
            "price",
            "cost",
            "how much",
            "available",
            "availability",
            "still active",
            "vacant",
            "more details",
            "details",
            "info",
            "information",
            "phone",
            "email",
            "contact",
            "number",
            "code",
            "entry code",
            "access code",
            "gate code",
            "lock code",
            "door code",
        )
        reply = ""
        intent = "unknown"

        if (
            budget_limit is not None
            and not self._looks_like_address_query(text)
            and not self.looks_like_explicit_property_reference(text)
        ):
            session["property_id"] = None
            session["last_match_type"] = None
            city, city_matches = self.find_city_matches(text, properties)
            budget, budget_matches = self.find_budget_matches(text, properties)
            if city and budget is not None:
                city_budget_matches = [
                    prop
                    for prop in city_matches
                    if prop.rent_per_month is not None and prop.rent_per_month <= budget
                ]
                if city_budget_matches:
                    city_budget_matches.sort(key=lambda prop: (prop.rent_per_month is None, prop.rent_per_month or 0, prop.name))
                    reply = self.add_footer(
                        self.list_properties_reply(city_budget_matches, f"{city} under ${int(budget):,}"),
                        None,
                    )
                else:
                    reply = self.add_footer(f"I could not find any properties in {city} under ${int(budget):,}.", None)
                intent = "budget_list"
            elif budget_matches:
                reply = self.add_footer(
                    self.list_properties_reply(budget_matches, f"${int(budget):,} budget"),
                    None,
                )
                intent = "budget_list"
            else:
                reply = self.add_footer(
                    f"I could not find any properties under ${int(budget_limit):,}. Please send the property address or area if you want me to narrow it down.",
                    None,
                )
                intent = "budget_list"

            message = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "phone": phone,
                "incoming": text,
                "reply": reply,
                "intent": intent,
                "property_id": None,
            }
            self.history.setdefault(phone, []).append(message)
            return message

        prop, match_type = self.find_property(text, session, properties)

        if (
            prop is None
            and session.get("property_id")
            and not self._looks_like_address_query(text)
            and any(term in normalized for term in detail_terms + code_terms)
        ):
            prop = self._session_property(session, properties)
            if prop is not None:
                match_type = "session"

        if session.get("human_handoff"):
            reply = self.add_footer(
                "A leasing specialist has been notified.",
                prop,
            )
            intent = "handoff"
        elif any(
            word in normalized
            for word in [
                "human",
                "agent",
                "person",
                "call me",
                "called",
                "no response",
                "no reply",
                "automated",
                "voicemail",
                "left a message",
                "return call",
                "trying the other numbers",
            ]
        ):
            session["human_handoff"] = True
            ttl_seconds = int(os.getenv("HANDOFF_TTL_SECONDS", str(DEFAULT_HANDOFF_TTL_SECONDS)))
            session["human_handoff_until"] = (
                datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            ).isoformat(timespec="seconds")
            reply = self.add_footer(
                (
                    "No problem. I can connect you with a leasing specialist. "
                    "Please share the property area or address if you have it."
                ),
                prop,
            )
            intent = "human_handoff"
        elif prop is None:
            if match_type == "address_like":
                reply = self.add_footer(
                    "I could not find that property. Please send the full address or area, and I'll narrow it down.",
                    None,
                )
                intent = "clarify_property"
            else:
                city, city_matches = self.find_city_matches(text, properties)
                budget, budget_matches = self.find_budget_matches(text, properties)
                if city and budget is not None:
                    city_budget_matches = [
                        prop
                        for prop in city_matches
                        if prop.rent_per_month is not None and prop.rent_per_month <= budget
                    ]
                    if city_budget_matches:
                        city_budget_matches.sort(key=lambda prop: (prop.rent_per_month is None, prop.rent_per_month or 0, prop.name))
                        reply = self.add_footer(
                            self.list_properties_reply(city_budget_matches, f"{city} under ${int(budget):,}"),
                            None,
                        )
                    else:
                        reply = self.add_footer(f"I could not find any properties in {city} under ${int(budget):,}.", None)
                    intent = "budget_list"
                elif city_matches:
                    reply = self.add_footer(self.list_properties_reply(city_matches, city), None)
                    intent = "area_list"
                else:
                    if budget_matches:
                        reply = self.add_footer(
                            self.list_properties_reply(budget_matches, f"${int(budget):,} budget"),
                            None,
                        )
                        intent = "budget_list"
                    else:
                        reply = self.add_footer(
                            (
                                "Which area are you looking to rent, like Allen, Frisco, or Plano? "
                                "Or send your max budget or the property address."
                            ),
                            None,
                        )
                        intent = "clarify_property"
                if intent == "clarify_property" and session.get("property_id") and not self._looks_like_address_query(text) and any(
                    term in normalized for term in detail_terms + code_terms
                ):
                    session_prop = self._session_property(session, properties)
                    if session_prop is not None:
                        prop = session_prop
                        match_type = "session"
                        intent = "property_qna"
                        reply = self.add_footer(self.answer_property_question(prop, normalized), prop)
        elif match_type == "partial":
            if any(term in normalized for term in property_info_terms):
                reply = self.add_footer(self.answer_property_question(prop, normalized), prop)
                intent = "property_qna"
            elif self.looks_like_explicit_property_reference(text):
                reply = self.add_footer(self.property_summary(prop), prop)
                intent = "property_qna"
            else:
                reply = self.add_footer(
                    (
                        f"I found {prop.name} at {prop.address}. "
                        "Do you want rent, availability, or bedroom details for this property?"
                    ),
                    prop,
                )
                intent = "property_suggestion"
        else:
            if any(term in normalized for term in property_info_terms):
                reply = self.add_footer(self.answer_property_question(prop, normalized), prop)
                intent = "property_qna"
            elif self.looks_like_explicit_property_reference(text):
                reply = self.add_footer(self.property_summary(prop), prop)
                intent = "property_qna"
            else:
                intent = "property_qna"
                reply = self.add_footer(self.answer_property_question(prop, normalized), prop)

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
    logger: MessageLogger | None = None

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

    def _log_message(self, record: MessageLogRecord) -> None:
        if self.logger is None:
            return
        try:
            self.logger.log(record)
        except Exception:
            return

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
        if parsed.path == "/api/app-info":
            return self._send_json(
                {
                    "app_name": "VP Realty SMS Pilot",
                    "version": APP_VERSION,
                    "release_notes_url": "/release-notes",
                }
            )
        if parsed.path == "/release-notes":
            notes_path = BASE_DIR / "docs" / "release-notes.md"
            if not notes_path.exists() or not notes_path.is_file():
                return self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            notes_text = escape(notes_path.read_text(encoding="utf-8"))
            return self._send_text(
                f"""<html>
  <head>
    <title>Release Notes - VP Realty SMS Pilot</title>
    <meta charset="utf-8" />
    <style>
      body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.6; }}
      pre {{ white-space: pre-wrap; background: #f7f7f7; padding: 16px; border-radius: 8px; }}
      a {{ color: #0b66ff; }}
    </style>
  </head>
  <body>
    <p><a href="/demo">Back to demo</a></p>
    <pre>{notes_text}</pre>
  </body>
</html>""",
                content_type="text/html; charset=utf-8",
            )
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
      <li><a href="/api/app-info">/api/app-info</a></li>
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
        if parsed.path == "/twilio/voice":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            form = parse_qs(raw)
            from_number = (form.get("From", [""]) or [""])[0].strip()
            to_number = (form.get("To", [""]) or [""])[0].strip()

            request_params = {key: values[0] for key, values in form.items()}
            request_url = self.security.external_url(self.path, dict(self.headers))
            signature = self.headers.get("X-Twilio-Signature", "")
            if not self.security.validate(request_url, request_params, signature):
                return self._send_xml(self._voice_twiml("Forbidden"), status=403)

            voice_message = (
                "Thanks for contacting VP Realty. Text 214-206-4345 with your question, "
                "and an agent will reply shortly."
            )
            self._log_message(
                MessageLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    direction="in-CALL",
                    from_number=from_number,
                    to_number=to_number,
                    message_text="Incoming call received; played SMS deflection prompt.",
                    status="received",
                )
            )
            sms_status = "sent"
            sms_error = ""
            if from_number:
                try:
                    outbound = self.messenger.send_sms(from_number, voice_message)
                    sms_status = str(outbound.get("status", "sent"))
                except Exception as exc:
                    sms_status = "error"
                    sms_error = str(exc)
            else:
                sms_status = "error"
                sms_error = "Missing caller phone number."

            self._log_message(
                MessageLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    direction="out-SMS-C",
                    from_number=to_number,
                    to_number=from_number,
                    message_text=voice_message,
                    status=sms_status,
                    error=sms_error,
                )
            )
            return self._send_xml(
                self._voice_twiml(voice_message)
            )

        if parsed.path == "/twilio/sms":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            form = parse_qs(raw)
            phone = (form.get("From", [""]) or [""])[0].strip()
            to_number = (form.get("To", [""]) or [""])[0].strip()
            text = (form.get("Body", [""]) or [""])[0].strip()
            if not phone or not text:
                return self._send_xml(self._twiml("Missing phone number or message."), status=400)

            request_params = {key: values[0] for key, values in form.items()}
            request_url = self.security.external_url(self.path, dict(self.headers))
            signature = self.headers.get("X-Twilio-Signature", "")
            if not self.security.validate(request_url, request_params, signature):
                return self._send_xml(self._twiml("Forbidden"), status=403)

            result = self.brain.respond(phone, text)
            self._log_message(
                MessageLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    direction="in-SMS",
                    from_number=phone,
                    to_number=to_number,
                    message_text=text,
                    property_id=str(result.get("property_id", "")),
                    intent=str(result.get("intent", "")),
                    status="received",
                )
            )
            try:
                outbound = self.messenger.send_sms(phone, result["reply"])
            except Exception as exc:
                self._log_message(
                    MessageLogRecord(
                        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        direction="out-SMS",
                        from_number=self.messenger.from_number or self.messenger.messaging_service_sid or "",
                        to_number=phone,
                        message_text=result["reply"],
                        property_id=str(result.get("property_id", "")),
                        intent=str(result.get("intent", "")),
                        status="error",
                        error=str(exc),
                    )
                )
                return self._send_xml(self._twiml(f"Twilio send failed: {exc}"), status=500)

            result["twilio"] = outbound
            self._log_message(
                MessageLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    direction="out-SMS",
                    from_number=self.messenger.from_number or self.messenger.messaging_service_sid or "",
                    to_number=phone,
                    message_text=result["reply"],
                    property_id=str(result.get("property_id", "")),
                    intent=str(result.get("intent", "")),
                    status=str(outbound.get("status", "sent")),
                )
            )
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
            to_number = self.messenger.from_number or self.messenger.messaging_service_sid or ""
            self._log_message(
                MessageLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    direction="in-SMS",
                    from_number=phone,
                    to_number=to_number,
                    message_text=text,
                    property_id=str(result.get("property_id", "")),
                    intent=str(result.get("intent", "")),
                    status="received",
                )
            )
            self._log_message(
                MessageLogRecord(
                    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    direction="out-SMS",
                    from_number=to_number,
                    to_number=phone,
                    message_text=str(result.get("reply", "")),
                    property_id=str(result.get("property_id", "")),
                    intent=str(result.get("intent", "")),
                    status="sent",
                )
            )
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

    def _voice_twiml(self, message: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f"<Response><Say>{escape(message)}</Say><Hangup /></Response>"
        )


def build_store_from_env() -> PropertyStore:
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip() or DEFAULT_GOOGLE_SHEET_ID
    worksheet_name = os.getenv("GOOGLE_SHEET_TAB", "ChatBotClient").strip()
    credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON", "").strip()
    csv_path = os.getenv("PROPERTIES_CSV_PATH", "").strip()
    source_url = os.getenv("PROPERTIES_SOURCE_URL", "").strip()
    source_format = os.getenv("PROPERTIES_SOURCE_FORMAT", "").strip()

    if sheet_id and (credentials_file or credentials_json):
        primary = GoogleSheetsPropertyStore(sheet_id, worksheet_name, credentials_file, credentials_json)
        if csv_path:
            return FallbackPropertyStore(primary, CsvPropertyStore(csv_path))
        return primary

    if source_url:
        return RemotePropertyStore(source_url, source_format)

    if csv_path:
        return CsvPropertyStore(csv_path)

    default_csv_path = BASE_DIR / "data" / "LeasingSnapshot - ChatBotClient.csv"
    if default_csv_path.exists():
        return CsvPropertyStore(str(default_csv_path))

    raise RuntimeError(
        "Set GOOGLE_SHEET_ID + GOOGLE_APPLICATION_CREDENTIALS for Google Sheets, "
        "PROPERTIES_SOURCE_URL for a remote CSV/JSON feed, "
        "or PROPERTIES_CSV_PATH for a local CSV fallback."
    )


def build_message_logger_from_env() -> MessageLogger:
    loggers: list[MessageLogger] = []
    if truthy_env("MESSAGE_LOG_TO_CONSOLE", "true"):
        loggers.append(ConsoleMessageLogger())
    web_app_url = os.getenv("MESSAGE_LOG_APPS_SCRIPT_URL", "").strip()
    secret = os.getenv("MESSAGE_LOG_APPS_SCRIPT_SECRET", "").strip()
    if web_app_url and truthy_env("MESSAGE_LOG_TO_APPS_SCRIPT", "false"):
        loggers.append(AppsScriptMessageLogger(web_app_url, secret))

    if loggers:
        return CompositeMessageLogger(loggers)
    return NoopMessageLogger()


def build_brain_and_services() -> tuple[ConversationBrain, TwilioMessenger, TwilioWebhookSecurity, MessageLogger]:
    store = build_store_from_env()
    brain = ConversationBrain(store)
    messenger = TwilioMessenger()
    security = TwilioWebhookSecurity()
    logger = build_message_logger_from_env()
    return brain, messenger, security, logger


def main() -> None:
    parser = argparse.ArgumentParser(description="VP Realty production SMS backend")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", default=int(os.getenv("PORT", "8000")), type=int)
    args = parser.parse_args()

    handler_cls = ProductionRequestHandler
    brain, messenger, security, logger = build_brain_and_services()
    handler_cls.brain = brain
    handler_cls.messenger = messenger
    handler_cls.security = security
    handler_cls.logger = logger
    server = ThreadingHTTPServer((args.host, args.port), handler_cls)
    print(f"ready {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
