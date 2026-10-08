import os
import unittest
from unittest.mock import patch

from services.llm_client import generate_chat_answer


class LlmClientTests(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "profile_label": "平衡型",
            "risk_score": 50.0,
            "gold_weight": 0.7,
            "bitcoin_weight": 0.3,
            "target_gold": 70000.0,
            "target_bitcoin": 30000.0,
            "gold_change": 70000.0,
            "bitcoin_change": 30000.0,
        }
        self.context = {"market_state": "normal"}

    @patch.dict(os.environ, {"LLM_API_KEY": "", "LLM_API_BASE": "", "LLM_MODEL": ""})
    def test_offline_chat_references_current_plan_for_plan_question(self):
        answer = generate_chat_answer(
            [{"role": "user", "content": "我的配置比例是什么？"}],
            self.plan,
            self.context,
        )
        self.assertIn("70.0%", answer)
        self.assertIn("30.0%", answer)

    @patch.dict(os.environ, {"LLM_API_KEY": "", "LLM_API_BASE": "", "LLM_MODEL": ""})
    def test_offline_chat_explains_drawdown_without_guarantee(self):
        answer = generate_chat_answer(
            [{"role": "user", "content": "回撤是什么意思？"}],
            self.plan,
            self.context,
        )
        self.assertIn("不是系统能够保证的亏损上限", answer)


if __name__ == "__main__":
    unittest.main()
