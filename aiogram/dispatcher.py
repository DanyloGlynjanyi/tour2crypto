"""Minimal Dispatcher stub."""

from __future__ import annotations

from typing import List

from .router import Router


class Dispatcher:
    """Store routers for later processing."""

    def __init__(self) -> None:
        self.routers: List[Router] = []

    def include_router(self, router: Router) -> None:
        if router not in self.routers:
            self.routers.append(router)
