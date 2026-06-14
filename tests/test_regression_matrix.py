from __future__ import annotations

import unittest

from tests.case_sets import build_case_matrix, load_property_records
from production_app import ConversationBrain, PropertyRecord, PropertyStore


class RegressionPropertyStore(PropertyStore):
    def __init__(self, records: list[PropertyRecord]):
        self._records = records

    def load(self) -> list[PropertyRecord]:
        return self._records


class RegressionMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_property_records()
        cls.store = RegressionPropertyStore(cls.records)
        cls.cases = build_case_matrix()

    def setUp(self) -> None:
        self.brain = ConversationBrain(self.store)

    def test_200_case_matrix(self) -> None:
        self.assertEqual(len(self.cases), 200)
        for index, case in enumerate(self.cases, 1):
            with self.subTest(index=index, label=case.label, prompt=case.prompt):
                phone = f"+1555{index:06d}"
                response = self.brain.respond(phone, case.prompt)
                self.assertEqual(response["intent"], case.expected_intent)
                if case.expected_property_id is None:
                    self.assertIsNone(response["property_id"])
                else:
                    self.assertEqual(str(response["property_id"]), case.expected_property_id)
                reply = str(response["reply"])
                if case.expected_reply is not None:
                    self.assertEqual(reply, case.expected_reply)
                for token in case.contains:
                    self.assertIn(token, reply)
                for token in case.not_contains:
                    self.assertNotIn(token, reply)


if __name__ == "__main__":
    unittest.main()
