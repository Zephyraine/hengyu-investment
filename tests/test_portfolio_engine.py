import json
import unittest
from pathlib import Path

from services.portfolio_engine import (
    calculate_personalized_plan,
    calculate_plan,
    calculate_risk_score,
    suggest_profile,
)
from services.response_guard import validate_advisor_payload


ROOT = Path(__file__).resolve().parents[1]


class PortfolioEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.allocation = json.loads(
            (ROOT / "data" / "app" / "final_allocation.json").read_text(encoding="utf-8")
        )

    def test_profile_order(self):
        weights = [
            self.allocation["profiles"][name]["target_weights"]["bitcoin"]
            for name in ("conservative", "balanced", "aggressive")
        ]
        self.assertEqual(weights, sorted(weights))

    def test_plan_sums_to_total(self):
        plan = calculate_plan("balanced", 100000, 10000, 5000, self.allocation)
        self.assertAlmostEqual(plan["target_gold"] + plan["target_bitcoin"], 100000)

    def test_questionnaire_boundaries(self):
        self.assertEqual(suggest_profile(1, 0.10, "低"), "conservative")
        self.assertEqual(suggest_profile(10, 0.50, "高"), "aggressive")

    def test_guard_blocks_weight_changes(self):
        plan = calculate_plan("balanced", 100000, 0, 0, self.allocation)
        payload = {
            "risk_profile": "balanced",
            "gold_weight": 0.5,
            "bitcoin_weight": 0.5,
            "summary": "test",
            "reasons": [],
            "warnings": [],
            "rebalance_message": "test",
        }
        valid, _ = validate_advisor_payload(payload, plan)
        self.assertFalse(valid)

    def test_continuous_risk_score_is_bounded(self):
        low, _ = calculate_risk_score(1, 0.10, "高", "立即清仓", 0)
        high, _ = calculate_risk_score(10, 0.50, "低", "逢低增加", 100)
        self.assertEqual(low, 0)
        self.assertEqual(high, 100)

    def test_personalized_plan_uses_continuous_anchor_interpolation(self):
        answers = {
            "horizon_years": 7,
            "max_drawdown": 0.20,
            "liquidity_need": "低",
            "loss_reaction": "继续持有",
            "bitcoin_acceptance": 66,
        }
        plan = calculate_personalized_plan(answers, 100000, 0, 0, self.allocation)
        balanced = self.allocation["profiles"]["balanced"]["target_weights"]["bitcoin"]
        aggressive = self.allocation["profiles"]["aggressive"]["target_weights"]["bitcoin"]
        self.assertGreater(plan["bitcoin_weight"], balanced)
        self.assertLess(plan["bitcoin_weight"], aggressive)
        self.assertAlmostEqual(plan["gold_weight"] + plan["bitcoin_weight"], 1.0)
        self.assertAlmostEqual(plan["target_gold"] + plan["target_bitcoin"], 100000)


if __name__ == "__main__":
    unittest.main()
