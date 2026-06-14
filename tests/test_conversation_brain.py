from __future__ import annotations

import csv
import unittest
from pathlib import Path

from production_app import ConversationBrain, PropertyRecord, PropertyStore


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "LeasingSnapshot - ChatBotClient.csv"


class StaticPropertyStore(PropertyStore):
    def __init__(self, records: list[PropertyRecord]):
        self._records = records

    def load(self) -> list[PropertyRecord]:
        return self._records


def load_property_records() -> list[PropertyRecord]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return [PropertyRecord.from_row(row) for row in csv.DictReader(f)]


class ConversationBrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_property_records()
        cls.store = StaticPropertyStore(cls.records)

    def setUp(self) -> None:
        self.brain = ConversationBrain(self.store)

    def respond(self, text: str, phone: str = "+15550000001") -> dict[str, object]:
        return self.brain.respond(phone, text)

    def get_property(self, property_id: str) -> PropertyRecord:
        for prop in self.records:
            if prop.property_id == property_id:
                return prop
        raise AssertionError(f"Property {property_id} not found in fixture data.")

    def test_contact_column_is_parsed(self) -> None:
        prop = self.get_property("1811")
        self.assertEqual(prop.manager_name, "Nishant Nanani")
        self.assertIn("nishant@vprealtyservices.com", prop.manager_email)
        self.assertIn("903-213-3818", prop.manager_phone)

    def test_exact_property_lookup_for_1009(self) -> None:
        resp = self.respond("1009 Riverstone Trail Princeton, TX 75407")
        self.assertEqual(resp["intent"], "property_qna")
        self.assertEqual(resp["property_id"], "373")
        reply = str(resp["reply"])
        self.assertIn("1009 Riverstone Trail", reply)
        self.assertIn("rent $2,195", reply)
        self.assertIn("available from Jun 10, 2026", reply)

    def test_budget_query_short_circuits_and_clears_property_context(self) -> None:
        phone = "+15550000002"
        first = self.brain.respond(phone, "1009 Riverstone Trail Princeton, TX 75407")
        self.assertEqual(first["property_id"], "373")

        second = self.brain.respond(phone, "I am looking for property under 2300 in frisco")
        self.assertEqual(second["intent"], "budget_list")
        self.assertIsNone(second["property_id"])
        reply = str(second["reply"])
        self.assertIn("Frisco under $2,300", reply)
        self.assertIn("Send your budget or the address", reply)

    def test_showing_followup_from_logs_stays_on_property(self) -> None:
        resp = self.respond(
            "Good morning, I requested a showing for 1009 Riverstone Trail in Princeton for tomorrow at 1130 am. Is there a better time for tomorrow I can show it?"
        )
        self.assertEqual(resp["intent"], "property_qna")
        self.assertEqual(resp["property_id"], "373")
        reply = str(resp["reply"])
        self.assertIn("1009 Riverstone Trail", reply)
        self.assertIn("For more details", reply)

    def test_contact_request_from_logs_uses_manager_contact(self) -> None:
        resp = self.respond("Who should I contact for details? 100 Stovall Lane Caddo Mills, TX 75135")
        self.assertEqual(resp["intent"], "property_qna")
        self.assertEqual(resp["property_id"], "1811")
        reply = str(resp["reply"])
        self.assertIn("903-213-3818", reply)
        self.assertIn("nishant@vprealtyservices.com", reply)
        self.assertEqual(reply.count("For more details"), 1)

    def test_entry_code_from_logs_uses_fixed_code_and_manager_phone(self) -> None:
        resp = self.respond("What is the entry code for this property? 100 Stovall Lane Caddo Mills, TX 75135")
        self.assertEqual(resp["intent"], "property_qna")
        self.assertEqual(resp["property_id"], "1811")
        reply = str(resp["reply"])
        self.assertIn("The entry code is 1975", reply)
        self.assertIn("contact the property manager at 903-213-3818", reply)
        self.assertNotIn("For more details, call the leasing team", reply)

    def test_area_typo_and_alias_matching(self) -> None:
        cases = [
            ("Princton", "Princeton"),
            ("McKinny", "McKinney"),
            ("North Princeton", "Princeton"),
        ]
        for text, expected_city in cases:
            with self.subTest(text=text):
                resp = self.respond(text)
                self.assertEqual(resp["intent"], "area_list")
                self.assertIsNone(resp["property_id"])
                reply = str(resp["reply"])
                self.assertIn(expected_city, reply)
                self.assertIn("options", reply)

    def test_buy_request_routes_to_area_list_instead_of_property_qna(self) -> None:
        resp = self.respond(
            "Hi Niketu, thanks. We're looking to buy (not rent) in Allen/Frisco/Plano-ideally a fixer that needs work. Do you have anything like that available or coming up soon? If so, what's the address?"
        )
        self.assertEqual(resp["intent"], "area_list")
        self.assertIsNone(resp["property_id"])
        reply = str(resp["reply"])
        self.assertIn("Frisco", reply)
        self.assertIn("options", reply)

    def test_call_request_from_logs_routes_to_area_list(self) -> None:
        resp = self.respond("Can you please give me a call about this property?")
        self.assertEqual(resp["intent"], "area_list")
        self.assertIsNone(resp["property_id"])
        self.assertIn("options", str(resp["reply"]))

    def test_property_not_listed_message_routes_to_area_list(self) -> None:
        resp = self.respond("This link says property is not listed on any platform. Can you update me on status?")
        self.assertEqual(resp["intent"], "area_list")
        self.assertIsNone(resp["property_id"])
        self.assertIn("options", str(resp["reply"]))

    def test_touring_request_with_address_keeps_property_context(self) -> None:
        resp = self.respond(
            "Hi, I am interested in touring a property you have listed at 635 Beltrand Ln, in Fate TX. I have tried to contact someone several times and have not heard back. May I please have more information on the property and when I can tour please and thank you!"
        )
        self.assertEqual(resp["intent"], "property_qna")
        self.assertEqual(resp["property_id"], "1508")
        reply = str(resp["reply"])
        self.assertIn("972-591-8075", reply)
        self.assertIn("anjali@vprealtyservices.com", reply)

    def test_no_response_message_triggers_handoff(self) -> None:
        resp = self.respond("I called a number of times now, but have gotten no response :-(")
        self.assertEqual(resp["intent"], "human_handoff")
        self.assertIsNone(resp["property_id"])
        reply = str(resp["reply"])
        self.assertIn("leasing specialist", reply)

    def test_application_fee_without_context_asks_for_area_or_address(self) -> None:
        resp = self.respond("What is the application fee?")
        self.assertEqual(resp["intent"], "clarify_property")
        self.assertIsNone(resp["property_id"])
        self.assertIn("Which area are you looking to rent", str(resp["reply"]))

    def test_availability_query_with_address(self) -> None:
        resp = self.respond("Is 1009 Riverstone Trail Princeton, TX 75407 still available for lease?")
        self.assertEqual(resp["intent"], "property_qna")
        self.assertEqual(resp["property_id"], "373")
        reply = str(resp["reply"])
        self.assertIn("currently Vacant-Rented", reply)

    def test_rent_query_with_address(self) -> None:
        resp = self.respond("How much is rent? 1009 Riverstone Trail Princeton, TX 75407")
        self.assertEqual(resp["intent"], "property_qna")
        self.assertEqual(resp["property_id"], "373")
        self.assertIn("$2,195 per month", str(resp["reply"]))

    def test_explicit_property_reference_summary(self) -> None:
        resp = self.respond("Thanks, Niketu-I appreciate the 1736 Hickory Chase Cir address.")
        self.assertEqual(resp["intent"], "property_qna")
        self.assertEqual(resp["property_id"], "280")
        reply = str(resp["reply"])
        self.assertIn("1736 Hickory Chase circle Keller, TX 76248", reply)
        self.assertIn("4 bedrooms, 3.0 bathrooms", reply)

    def test_ambiguous_rent_only_message_falls_back_to_area_list(self) -> None:
        resp = self.respond("How much is rent?")
        self.assertEqual(resp["intent"], "area_list")
        self.assertIsNone(resp["property_id"])
        self.assertIn("Howe options", str(resp["reply"]))


if __name__ == "__main__":
    unittest.main()
