"""Unit tests for the deterministic purchase decision rules."""

import sys
import unittest
from datetime import date
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from budget_advisor import evaluate_purchase, month_bounds  # noqa: E402


class EvaluatePurchaseTests(unittest.TestCase):
    def evaluate(self, *, price=100, spent=400, budget=1000):
        return evaluate_purchase(
            item_name="running shoes",
            price=price,
            category_name="Shopping",
            expense_type="variable",
            period_start=date(2026, 7, 1),
            period_end=date(2026, 8, 1),
            budget_scope="variable_envelope",
            budget_amount=budget,
            spent_so_far=spent,
        )

    def test_purchase_within_budget(self):
        result = self.evaluate()

        self.assertEqual(result["decision"], "within_budget")
        self.assertTrue(result["can_buy_within_budget"])
        self.assertEqual(result["remaining_after_purchase"], 500.0)
        self.assertEqual(result["projected_utilisation_pct"], 50.0)

    def test_purchase_marks_tight_at_ninety_percent(self):
        result = self.evaluate(price=100, spent=800)

        self.assertEqual(result["decision"], "tight")
        self.assertTrue(result["can_buy_within_budget"])
        self.assertEqual(result["remaining_after_purchase"], 100.0)

    def test_purchase_over_budget(self):
        result = self.evaluate(price=100, spent=950)

        self.assertEqual(result["decision"], "over_budget")
        self.assertFalse(result["can_buy_within_budget"])
        self.assertEqual(result["remaining_after_purchase"], -50.0)

    def test_missing_budget_does_not_guess(self):
        result = self.evaluate(budget=None)

        self.assertEqual(result["decision"], "no_budget")
        self.assertIsNone(result["can_buy_within_budget"])
        self.assertIsNone(result["remaining_after_purchase"])

    def test_zero_budget_is_over_budget_without_fake_utilisation(self):
        result = self.evaluate(budget=0)

        self.assertEqual(result["decision"], "over_budget")
        self.assertFalse(result["can_buy_within_budget"])
        self.assertIsNone(result["projected_utilisation_pct"])

    def test_month_bounds_handle_year_end(self):
        self.assertEqual(
            month_bounds(date(2026, 12, 20)),
            (date(2026, 12, 1), date(2027, 1, 1)),
        )


if __name__ == "__main__":
    unittest.main()
