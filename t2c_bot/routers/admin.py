"""Admin router providing simulation utilities."""

from __future__ import annotations

from decimal import Decimal

from aiogram import Router
from aiogram.types import Message

from t2c_core import metrics as core_metrics
from t2c_core.logging import get_logger
from t2c_contracts.factories import TripFactory
from t2c_logic.handlers import (
    ledger_entries,
    rules_ledger,
    set_trip_reward,
    wallets,
)
from t2c_pipeline.collector import collect_trip_completed, collect_withdrawal_paid
from t2c_pipeline.metrics import snapshot as metrics_snapshot

from .. import BotContext

router = Router(name="admin")
_context: BotContext | None = None
LOGGER = get_logger(__name__)


def setup(context: BotContext) -> Router:
    """Attach shared context and return the router."""

    global _context
    _context = context
    return router


async def _drain_queue() -> None:
    if _context is None:
        return
    while True:
        processed = await _context.worker.run_once()
        if not processed:
            break


def _default_wallet_id() -> str | None:
    if not wallets:
        return None
    return next(iter(wallets.keys()))


@router.message(commands={"admin"})
async def handle_admin(message: Message) -> None:
    """Display ledger counters and metrics."""

    core_metrics.inc("bot_actions")
    LOGGER.info("Admin opened dashboard")
    wallet_count = len(wallets)
    ledger_count = len(ledger_entries)
    rule_events = len(rules_ledger)
    metrics = metrics_snapshot()
    queue_size = _context.queue.qsize() if _context is not None else 0
    await message.answer(
        "Admin панель\nКористувачів: {wallets}\nЛеджерних записів: {ledger}\n"
        "Інваріантів: {rules}\nЧерга: {queue}\nМетрики: {metrics}".format(
            wallets=wallet_count,
            ledger=ledger_count,
            rules=rule_events,
            queue=queue_size,
            metrics=metrics,
        )
    )


@router.message(text="Симуляція trip_completed")
async def handle_trip_completed_simulation(message: Message) -> None:
    """Trigger cashback accrual for a synthetic trip."""

    core_metrics.inc("bot_actions")
    LOGGER.info("Admin triggered trip_completed simulation")
    if _context is None:
        await message.answer("Контекст недоступний.")
        return

    wallet_id = _default_wallet_id()
    if wallet_id is None:
        await message.answer("Немає доступних гаманців для симуляції.")
        return

    wallet = wallets[wallet_id]
    trip_payload = TripFactory().build(traveler_id=wallet.owner_id, status="completed")
    set_trip_reward(trip_payload["id"], Decimal("12.50"))
    event = collect_trip_completed(wallet.owner_id, trip_payload["id"])
    await _context.queue.put(event)
    _context.published_events.append(event)
    await _drain_queue()

    await message.answer(
        "Симульовано завершення поїздки {trip_id}.".format(trip_id=trip_payload["id"])
    )


@router.message(text="Показати dead-letters")
async def handle_dead_letters(message: Message) -> None:
    """List dead-lettered events accumulated by the worker."""

    core_metrics.inc("bot_actions")
    LOGGER.info("Admin requested dead-letter list")
    if _context is None:
        await message.answer("Контекст недоступний.")
        return

    if not _context.worker.dead_letters:
        await message.answer("Dead-letter черга порожня.")
        return

    lines = [
        "dead-letter: {event_type} ({event_id})".format(
            event_type=envelope["event"]["event_type"],
            event_id=envelope["event"]["event_id"],
        )
        for envelope in _context.worker.dead_letters
    ]
    await message.answer("\n".join(lines))


@router.message(text="Симуляція payout")
async def handle_payout_simulation(message: Message) -> None:
    """Simulate paying out the most recent withdrawal request."""

    core_metrics.inc("bot_actions")
    LOGGER.info("Admin triggered payout simulation")
    if _context is None:
        await message.answer("Контекст недоступний.")
        return

    if not _context.pending_withdrawals:
        await message.answer("Немає очікуючих заявок на вивід.")
        return

    withdrawal_id, _ = next(iter(_context.pending_withdrawals.items()))
    event = collect_withdrawal_paid(withdrawal_id, "TX-SIMULATED", "0.50")
    await _context.queue.put(event)
    _context.published_events.append(event)
    await _drain_queue()
    _context.pending_withdrawals.pop(withdrawal_id, None)

    await message.answer(
        "Симуляція виплати завершена для {withdrawal_id}.".format(
            withdrawal_id=withdrawal_id
        )
    )


__all__ = ["router", "setup"]
