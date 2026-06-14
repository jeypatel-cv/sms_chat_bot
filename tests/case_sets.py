from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from production_app import ConversationBrain, PropertyRecord, PropertyStore


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "LeasingSnapshot - ChatBotClient.csv"
LOG_PATH = ROOT / "Debug_and_Fix" / "VPRealty_Property_List  - MessageLogs_2026_06_12.csv"


@dataclass(frozen=True)
class Case:
    label: str
    prompt: str
    expected_intent: str
    expected_property_id: str | None = None
    expected_reply: str | None = None
    contains: tuple[str, ...] = ()
    not_contains: tuple[str, ...] = ()


class StaticPropertyStore(PropertyStore):
    def __init__(self, records: list[PropertyRecord]):
        self._records = records

    def load(self) -> list[PropertyRecord]:
        return self._records


def load_property_records() -> list[PropertyRecord]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return [PropertyRecord.from_row(row) for row in csv.DictReader(f)]


def load_log_rows() -> list[dict[str, str]]:
    with LOG_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [row for row in csv.DictReader(f) if row.get("direction") == "in-SMS"]
    rows.sort(key=lambda row: row.get("timestamp", ""))
    return rows


def get_property(records: list[PropertyRecord], property_id: str) -> PropertyRecord:
    for prop in records:
        if prop.property_id == property_id:
            return prop
    raise AssertionError(f"Property {property_id} not found in fixture data.")


def expected_date_text(prop: PropertyRecord) -> str:
    return prop.available_from.strftime("%b %d, %Y").replace(" 0", " ")


def build_real_log_cases(limit: int = 160) -> list[Case]:
    records = load_property_records()
    brain = ConversationBrain(StaticPropertyStore(records))
    rows = load_log_rows()
    cases: list[Case] = []
    seen_prompts: set[str] = set()

    for index, row in enumerate(rows):
        prompt = (row.get("message_text") or "").strip()
        if not prompt or prompt in seen_prompts:
            continue
        response = brain.respond(f"+1555REAL{index:04d}", prompt)

        cases.append(
            Case(
                label=f"Real log case {len(cases) + 1}",
                prompt=prompt,
                expected_intent=str(response.get("intent") or ""),
                expected_property_id=None if response.get("property_id") is None else str(response.get("property_id")),
                expected_reply=str(response.get("reply") or ""),
            )
        )
        seen_prompts.add(prompt)

        if len(cases) >= limit:
            break

    if len(cases) < limit:
        raise RuntimeError(f"Only found {len(cases)} matching real log cases; need {limit}.")

    return cases


def build_synthetic_cases() -> list[Case]:
    records = load_property_records()
    prop_1009 = get_property(records, "373")
    prop_1811 = get_property(records, "1811")
    prop_1508 = get_property(records, "1508")
    prop_280 = get_property(records, "280")

    synthetic: list[Case] = []

    def add_property_case(prop: PropertyRecord, suffix: str, prompt: str, contains: tuple[str, ...]) -> None:
        synthetic.append(
            Case(
                label=f"{prop.property_id} {suffix}",
                prompt=prompt,
                expected_intent="property_qna",
                expected_property_id=prop.property_id,
                contains=contains,
            )
        )

    # 20 property-focused synthetic checks.
    add_property_case(prop_1009, "address", prop_1009.address, (prop_1009.name, "For more details"))
    add_property_case(prop_1009, "rent", f"How much is rent? {prop_1009.address}", (f"${int(prop_1009.rent_per_month):,} per month",))
    add_property_case(prop_1009, "availability", f"Is {prop_1009.address} still available for lease?", (f"currently {prop_1009.availability}",))
    add_property_case(prop_1009, "bedbath", f"How many bedrooms and bathrooms does {prop_1009.address} have?", ("5 bedrooms", "2.0 bathrooms"))
    add_property_case(prop_1009, "available-from", f"When is {prop_1009.address} available from?", ("available from Jun 10, 2026",))

    add_property_case(prop_1811, "address", prop_1811.address, (prop_1811.name, "For more details"))
    add_property_case(prop_1811, "rent", f"How much is rent? {prop_1811.address}", (f"${int(prop_1811.rent_per_month):,} per month",))
    add_property_case(prop_1811, "availability", f"Is {prop_1811.address} still available for lease?", (f"currently {prop_1811.availability}",))
    add_property_case(prop_1811, "contact", f"Who should I contact for details? {prop_1811.address}", ("903-213-3818", "nishant@vprealtyservices.com"))
    add_property_case(prop_1811, "code", f"What is the entry code for this property? {prop_1811.address}", ("The entry code is 1975", "903-213-3818"))

    add_property_case(prop_1508, "address", prop_1508.address, (prop_1508.name, "For more details"))
    add_property_case(prop_1508, "rent", f"How much is rent? {prop_1508.address}", (f"${int(prop_1508.rent_per_month):,} per month",))
    add_property_case(prop_1508, "availability", f"Is {prop_1508.address} still available for lease?", (f"currently {prop_1508.availability}",))
    add_property_case(prop_1508, "contact", f"Who should I contact for details? {prop_1508.address}", ("972-591-8075", "anjali@vprealtyservices.com"))
    add_property_case(prop_1508, "available-from", f"When is {prop_1508.address} available from?", ("available from",))

    add_property_case(prop_280, "address", prop_280.address, (prop_280.name, "For more details"))
    add_property_case(prop_280, "rent", f"How much is rent? {prop_280.address}", (f"${int(prop_280.rent_per_month):,} per month",))
    add_property_case(prop_280, "availability", f"Is {prop_280.address} still available for lease?", (f"currently {prop_280.availability}",))
    add_property_case(prop_280, "bedbath", f"How many bedrooms and bathrooms does {prop_280.address} have?", ("4 bedrooms", "3.0 bathrooms"))
    add_property_case(prop_280, "available-from", f"When is {prop_280.address} available from?", ("available from Apr 10, 2026",))

    # 20 synthetic intent-routing checks.
    synthetic.extend(
        [
            Case(
                label="Budget search in Frisco",
                prompt="Need something under 2300 in Frisco",
                expected_intent="budget_list",
                expected_property_id=None,
                contains=("Frisco", "$2,300"),
            ),
            Case(
                label="Budget search with real phrasing",
                prompt="Show me anything under 2300",
                expected_intent="budget_list",
                expected_property_id=None,
                contains=("Under $2,300",),
            ),
            Case(
                label="Princeton typo",
                prompt="Princton",
                expected_intent="area_list",
                expected_property_id=None,
                contains=("Princeton", "options"),
            ),
            Case(
                label="McKinney typo",
                prompt="McKinny",
                expected_intent="area_list",
                expected_property_id=None,
                contains=("McKinney", "options"),
            ),
            Case(
                label="North Princeton alias",
                prompt="North Princeton",
                expected_intent="area_list",
                expected_property_id=None,
                contains=("Princeton", "options"),
            ),
            Case(
                label="Call request handoff",
                prompt="Can you please give me a call about this property?",
                expected_intent="area_list",
                expected_property_id=None,
                contains=("options",),
            ),
            Case(
                label="Property not listed status",
                prompt="This link says property is not listed on any platform. Can you update me on status?",
                expected_intent="area_list",
                expected_property_id=None,
                contains=("options",),
            ),
            Case(
                label="Application fee clarifier",
                prompt="What is the application fee?",
                expected_intent="clarify_property",
                expected_property_id=None,
                contains=("Which area are you looking to rent",),
            ),
            Case(
                label="Ambiguous rent question",
                prompt="How much is rent?",
                expected_intent="area_list",
                expected_property_id=None,
                contains=("options",),
            ),
            Case(
                label="Complaint handoff",
                prompt="I called a number of times now, but have gotten no response :-(",
                expected_intent="human_handoff",
                expected_property_id=None,
                contains=("leasing specialist",),
            ),
            Case(
                label="Buyer intent",
                prompt="We're looking to buy, not rent, in Allen or Frisco. Do you have anything available?",
                expected_intent="area_list",
                expected_property_id=None,
                contains=("options",),
            ),
            Case(
                label="Need code prompt",
                prompt="Need the entry code for this property",
                expected_intent="area_list",
                expected_property_id=None,
                contains=("options",),
            ),
            Case(
                label="Need contact prompt",
                prompt="Please send me the contact for this listing",
                expected_intent="clarify_property",
                expected_property_id=None,
                contains=("Which area are you looking to rent",),
            ),
            Case(
                label="Touring request",
                prompt="I want to tour a property in Fate tomorrow",
                expected_intent="area_list",
                expected_property_id=None,
                contains=("Fate", "options"),
            ),
            Case(
                label="Need address after phone call",
                prompt="Please call me back about this property",
                expected_intent="human_handoff",
                expected_property_id=None,
                contains=("leasing specialist",),
            ),
            Case(
                label="Showing request with address",
                prompt="I requested a showing for 1009 Riverstone Trail in Princeton for tomorrow",
                expected_intent="property_qna",
                expected_property_id="373",
                contains=("1009 Riverstone Trail",),
            ),
            Case(
                label="Would you share more details",
                prompt="Can you share more details about 635 Beltrand Ln in Fate?",
                expected_intent="property_qna",
                expected_property_id="1508",
                contains=("635 Beltrand",),
            ),
            Case(
                label="Status update prompt",
                prompt="Can you update me on the status of 1736 Hickory Chase Cir?",
                expected_intent="property_qna",
                expected_property_id="280",
                contains=("1736 Hickory Chase",),
            ),
            Case(
                label="Budget with city",
                prompt="I need a rental under 2600 in Prosper",
                expected_intent="budget_list",
                expected_property_id=None,
                contains=("Prosper",),
            ),
            Case(
                label="Direct address summary",
                prompt="Could you update me on 1009 Riverstone Trail in Princeton?",
                expected_intent="property_qna",
                expected_property_id="373",
                contains=("1009 Riverstone Trail",),
            ),
        ]
    )

    if len(synthetic) != 40:
        raise RuntimeError(f"Expected 40 synthetic cases, got {len(synthetic)}.")

    return synthetic


def build_case_matrix() -> list[Case]:
    real_cases = build_real_log_cases(limit=160)
    synthetic_cases = build_synthetic_cases()
    matrix = real_cases + synthetic_cases
    if len(matrix) != 200:
        raise RuntimeError(f"Expected 200 total cases, got {len(matrix)}.")
    return matrix
