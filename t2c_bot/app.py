"""Executable entry point for the Tour2Crypto bot."""

from __future__ import annotations

import asyncio

from t2c_logic.handlers import get_wallet_balance, wallet_balances

from . import BotApp, create_bot_app
from .config import get_config


async def _run_pipeline_demo() -> None:
    """Execute the existing pipeline demonstration flow."""

    from scripts.pipeline_demo import run_demo

    await run_demo()


def _summarize_wallets(app: BotApp) -> str:
    if not wallet_balances:
        return "0.00"
    wallet_id, _ = next(iter(wallet_balances.items()))
    return get_wallet_balance(wallet_id)


def main() -> str:
    """Launch the bot in simulation mode and return a status string."""

    config = get_config()
    app = create_bot_app(config)

    if config.mode == "simulation":
        asyncio.run(_run_pipeline_demo())
        final_balance = _summarize_wallets(app)
        message = "BOT SIMULATION MODE OK"
        print(message)
        print("Registered routers:", len(app.routers))
        print("Final available balance:", final_balance)
        return message

    # Placeholder for future interactive modes.
    print("BOT READY (no polling in offline environment)")
    return "BOT READY"


if __name__ == "__main__":
    main()
