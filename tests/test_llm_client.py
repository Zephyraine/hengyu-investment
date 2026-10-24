import os
import unittest
from unittest.mock import patch

import requests

from services.llm_client import _chat_endpoint, generate_chat_answer, is_llm_configured


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

    @patch.dict(
        os.environ,
        {
            "LLM_API_KEY": "test-key",
            "LLM_API_BASE": "https://provider.example/v1",
            "LLM_MODEL": "test-model",
        },
    )
    def test_configured_status_accepts_environment_settings(self):
        self.assertTrue(is_llm_configured())

    def test_endpoint_does_not_duplicate_chat_path(self):
        endpoint = _chat_endpoint(
            "https://provider.example/v1/chat/completions", "/chat/completions"
        )
        self.assertEqual(endpoint, "https://provider.example/v1/chat/completions")

    @patch("services.llm_client._post_chat", side_effect=requests.ConnectionError("offline"))
    @patch.dict(
        os.environ,
        {
            "LLM_API_KEY": "test-key",
            "LLM_API_BASE": "https://provider.example/v1",
            "LLM_MODEL": "test-model",
        },
    )
    def test_online_failure_falls_back_without_exposing_exception(self, _post_chat):
        answer = generate_chat_answer(
            [{"role": "user", "content": "我的配置比例是什么？"}],
            self.plan,
            self.context,
        )
        self.assertIn("已切换为本地说明", answer)
        self.assertIn("70.0%", answer)
        self.assertNotIn("offline", answer)


if __name__ == "__main__":
    unittest.main()

