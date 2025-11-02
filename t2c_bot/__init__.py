"""Bot facade wiring routers with shared context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from aiogram import Bot, Dispatcher, Router

from t2c_events import EventBus, InMemoryIdempotencyStore
from t2c_logic import bus as logic_bus
from t2c_pipeline import AsyncEventQueue, EventWorker, reset_metrics
from t2c_pipeline.collector import reset_withdrawal_context

from .config import BotConfig


@dataclass
class BotContext:
    """Shared pipeline context for routers."""

    bus: EventBus
    queue: AsyncEventQueue
    worker: EventWorker
    store: InMemoryIdempotencyStore
    pending_withdrawals: Dict[str, str] = field(default_factory=dict)
    published_events: List[Dict[str, Any]] = field(default_factory=list)


class BotApp:
    """Facade that owns the bot, dispatcher, and routers."""

    def __init__(self, bot: Bot, dispatcher: Dispatcher, context: BotContext) -> None:
        self.bot = bot
        self.dispatcher = dispatcher
        self.context = context
        self.routers: List[Router] = []

    def include_router(self, router: Router) -> None:
        if router not in self.routers:
            self.routers.append(router)
        self.dispatcher.include_router(router)

    def setup(self) -> None:
        """Attach default routers to the dispatcher."""

        from .routers import admin, user

        self.include_router(user.setup(self.context))
        self.include_router(admin.setup(self.context))


def create_bot_app(config: BotConfig) -> BotApp:
    """Return a fully wired :class:`BotApp`."""

    reset_metrics()
    reset_withdrawal_context()
    queue = AsyncEventQueue()
    store = InMemoryIdempotencyStore()
    worker = EventWorker(logic_bus, queue, store)
    context = BotContext(bus=logic_bus, queue=queue, worker=worker, store=store)
    app = BotApp(Bot(config.token), Dispatcher(), context)
    app.setup()
    return app


__all__ = ["BotContext", "BotApp", "create_bot_app"]
