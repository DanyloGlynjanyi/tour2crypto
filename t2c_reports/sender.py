"""Telegram sender shim for reporting."""

from __future__ import annotations

import asyncio
from typing import Optional

from aiogram import Bot

from t2c_core import metrics as core_metrics
from t2c_core.logging import get_logger
from t2c_bot.config import get_config

LOGGER = get_logger(__name__)


async def _send_async(token: str, chat_id: int, text: str) -> None:
    bot = Bot(token)
    await bot.send_message(str(chat_id), text)


def send_report_via_telegram(text: str, mode: Optional[str] = None) -> str:
    """Send the given report text via Telegram or simulation."""

    config = get_config()
    effective_mode = mode or config.mode
    if effective_mode == "simulation" or config.token.startswith("FAKE_"):
        message = f"[SIMULATION] {text}"
        LOGGER.info("Report simulation: %s", text.splitlines()[0] if text else "(empty)")
        core_metrics.inc("reports_sent")
        print(message)
        return message

    try:
        asyncio.run(_send_async(config.token, config.admin_chat_id, text))
    except Exception as exc:  # noqa: BLE001
        LOGGER.error("Report delivery failed: %s", exc)
        message = f"[SIMULATION] send failed: {exc}"
        print(message)
        return message

    confirmation = "[SENT] Report delivered"
    LOGGER.info("Report delivered to Telegram")
    core_metrics.inc("reports_sent")
    print(confirmation)
    return confirmation


__all__ = ["send_report_via_telegram"]
