from __future__ import annotations

from t2c_bot.app import main


def test_bot_simulation_returns_status() -> None:
    result = main()
    assert result == "BOT SIMULATION MODE OK"
