"""User-facing router for the Tour2Crypto bot."""

from __future__ import annotations

from decimal import Decimal
from typing import Set

from aiogram import Router
from aiogram.types import Message

from t2c_core import metrics as core_metrics
from t2c_core.logging import get_logger
from t2c_logic.handlers import get_wallet_balance, ledger_entries, wallets
from t2c_pipeline.collector import collect_withdrawal_requested

from .. import BotContext

router = Router(name="user")
_context: BotContext | None = None
LOGGER = get_logger(__name__)


def setup(context: BotContext) -> Router:
    """Attach shared context and return the router."""

    global _context
    _context = context
    return router


def _first_wallet():
    if not wallets:
        return None
    return next(iter(wallets.values()))


def _cashback_total(wallet_id: str) -> str:
    total = Decimal("0.00")
    for entry in ledger_entries:
        if entry.wallet_id == wallet_id and entry.entry_type == "cashback":
            total += Decimal(entry.amount)
    return f"{total:.2f}"


def _trip_count(wallet_id: str) -> int:
    trips: Set[str] = set()
    for entry in ledger_entries:
        if entry.wallet_id == wallet_id and entry.entry_type == "cashback":
            trips.add(entry.trip_id)
    return len(trips)


async def _drain_queue() -> None:
    if _context is None:
        return
    while True:
        processed = await _context.worker.run_once()
        if not processed:
            break


@router.message(commands={"start"})
async def handle_start(message: Message) -> None:
    """Greet the user and highlight available actions."""

    core_metrics.inc("bot_actions")
    LOGGER.info("User invoked /start")
    await message.answer(
        "Вітаємо у Tour2Crypto! Виберіть опцію: \n"
        "• Мій баланс\n"
        "• Запросити вивід"
    )


@router.message(text="Мій баланс")
async def handle_balance(message: Message) -> None:
    """Display cached balance, cashback total, and trip count."""

    core_metrics.inc("bot_actions")
    LOGGER.info("User requested balance")
    wallet = _first_wallet()
    if wallet is None:
        await message.answer("Гаманець поки не створено у системі.")
        return

    balance = get_wallet_balance(wallet.id)
    cashback = _cashback_total(wallet.id)
    trips = _trip_count(wallet.id)
    await message.answer(
        "Ваш гаманець: {wallet}\nДоступний баланс: {balance} USDT\n"
        "Нараховано кешбеку: {cashback} USDT\nКількість поїздок: {trips}".format(
            wallet=wallet.id, balance=balance, cashback=cashback, trips=trips
        )
    )


@router.message(text="Запросити вивід")
async def handle_withdrawal_request(message: Message) -> None:
    """Simulate a withdrawal request via the event pipeline."""

    core_metrics.inc("bot_actions")
    LOGGER.info("User requested withdrawal simulation")
    if _context is None:
        await message.answer("Пайплайн недоступний у цьому режимі.")
        return

    wallet = _first_wallet()
    if wallet is None:
        await message.answer("Гаманець не знайдено для поточного користувача.")
        return

    balance = Decimal(get_wallet_balance(wallet.id))
    if balance <= Decimal("0.00"):
        await message.answer("Баланс недостатній для ініціювання виводу.")
        return

    event = collect_withdrawal_requested(wallet.owner_id, wallet.id, f"{balance:.2f}")
    await _context.queue.put(event)
    withdrawal_id = event["payload"]["withdrawal_request_id"]
    _context.pending_withdrawals[withdrawal_id] = wallet.id
    _context.published_events.append(event)
    await _drain_queue()

    await message.answer(
        "Запит на вивід створено. ID запиту: {withdrawal_id}."
        .format(withdrawal_id=withdrawal_id)
    )


__all__ = ["router", "setup"]
