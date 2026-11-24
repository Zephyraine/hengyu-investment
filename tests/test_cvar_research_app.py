from pathlib import Path

from streamlit.testing.v1 import AppTest

from services.cvar_research_service import (
    SCENARIOS,
    get_latest_target,
    get_strategy_metrics,
    get_target_history,
    get_three_arm_metrics,
    load_cvar_research_data,
)


ROOT = Path(__file__).resolve().parents[1]


def test_new_research_data_contract() -> None:
    data = load_cvar_research_data()
    assert len(data["metrics"]) == 9
    assert set(data["metrics"]["strategy"]) == {
        "GOLD_BTC",
        "GOLD_BTC_CASH",
        "GOLD_BTC_STABLE",
    }
    for scenario in SCENARIOS:
        assert get_strategy_metrics(data, scenario)["orders"] == 48
        assert len(get_three_arm_metrics(data, scenario)) == 3


def test_balanced_target_files_are_aligned_and_complete() -> None:
    data = load_cvar_research_data()
    scenario = "情景B｜收益风险权衡"
    histories = [
        get_target_history(data, scenario, strategy)
        for strategy in ["GOLD_BTC", "GOLD_BTC_CASH", "GOLD_BTC_STABLE"]
    ]
    assert all(len(history) == 48 for history in histories)
    assert histories[0]["date"].reset_index(drop=True).equals(histories[1]["date"].reset_index(drop=True))
    assert histories[0]["date"].reset_index(drop=True).equals(histories[2]["date"].reset_index(drop=True))
    latest = get_latest_target(data, scenario)
    assert latest is not None
    assert abs(latest["GOLD"] - 0.7410305793198364) < 1e-12
    assert abs(latest["BTC"] - 0.2589694206801636) < 1e-12
    assert get_latest_target(data, "情景A｜尾部风险优先") is None


def test_all_pages_render_without_streamlit_exceptions() -> None:
    app = AppTest.from_file(ROOT / "app.py", default_timeout=30).run()
    assert not app.exception
    pages = ["首页", "环境与证据", "双资产配置", "稳定币研究", "见微 Agent"]
    assert app.radio[0].options == pages
    for page in pages:
        app.radio[0].set_value(page).run()
        assert not app.exception, page

