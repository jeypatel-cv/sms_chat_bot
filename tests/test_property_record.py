from __future__ import annotations

import csv
import unittest
from pathlib import Path

from production_app import PropertyRecord


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "LeasingSnapshot - ChatBotClient.csv"


class PropertyRecordParsingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
            cls.rows = list(csv.DictReader(f))

    def row_for(self, property_id: str) -> dict[str, str]:
        for row in self.rows:
            if row.get("property_id") == property_id:
                return row
        raise AssertionError(f"Property {property_id} not found in fixture data.")

    def test_contact_column_maps_into_manager_fields(self) -> None:
        row = self.row_for("1811")
        prop = PropertyRecord.from_row(row)
        self.assertEqual(prop.manager_name, "Nishant Nanani")
        self.assertIn("nishant@vprealtyservices.com", prop.manager_email)
        self.assertIn("903-213-3818", prop.manager_phone)

    def test_contact_column_alias_is_accepted(self) -> None:
        row = {
            "property_id": "9999",
            "property_name": "Demo Home",
            "street": "123 Demo St",
            "city": "Demo City",
            "state": "TX",
            "zip": "75000",
            "bed_and_bath": "3/2",
            "advertised_rent": "1800",
            "unit_status": "Vacant-Unrented",
            "available_on": "2026-06-01",
            "contact": "Jane Doe: jane@example.com: 972-555-1212",
        }
        prop = PropertyRecord.from_row(row)
        self.assertEqual(prop.manager_name, "Jane Doe")
        self.assertEqual(prop.manager_email, "jane@example.com")
        self.assertEqual(prop.manager_phone, "972-555-1212")
        self.assertEqual(prop.address, "123 Demo St, Demo City, TX, 75000")

    def test_address_is_reconstructed_from_street_fields(self) -> None:
        row = {
            "property_id": "1000",
            "property_name": "",
            "street": "456 Oak Lane",
            "street2": "Unit 2",
            "city": "Plano",
            "state": "TX",
            "zip": "75024",
            "bed_and_bath": "4/3",
            "advertised_rent": "2500",
            "unit_status": "Vacant-Unrented",
            "available_on": "2026-06-15",
        }
        prop = PropertyRecord.from_row(row)
        self.assertEqual(prop.address, "456 Oak Lane, Unit 2, Plano, TX, 75024")
        self.assertEqual(prop.name, "456 Oak Lane")
        self.assertEqual(prop.city, "Plano")
        self.assertEqual(prop.bedrooms, 4)
        self.assertEqual(prop.bathrooms, 3)


if __name__ == "__main__":
    unittest.main()
