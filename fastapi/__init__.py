"""Minimal FastAPI-compatible shim for offline testing."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Any = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def Query(default: Any = None, *_: Any, **__: Any) -> Any:
    """Return the provided default value (metadata ignored)."""

    return default


@dataclass
class Route:
    method: str
    path: str
    handler: Callable[..., Any]
    response_class: Any

    def match(self, request_path: str) -> Optional[Dict[str, str]]:
        if self.path == request_path:
            return {}
        route_parts = [part for part in self.path.strip("/").split("/") if part]
        request_parts = [part for part in request_path.strip("/").split("/") if part]
        if len(route_parts) != len(request_parts):
            return None
        params: Dict[str, str] = {}
        for route_part, request_part in zip(route_parts, request_parts):
            if route_part.startswith("{") and route_part.endswith("}"):
                key = route_part.strip("{}")
                params[key] = request_part
            elif route_part != request_part:
                return None
        return params


class FastAPI:
    def __init__(self, title: str | None = None) -> None:
        self.title = title or "FastAPI"
        self.routes: List[Route] = []
        self.state = SimpleNamespace()

    def _add_route(self, method: str, path: str, handler: Callable[..., Any], response_class: Any) -> None:
        self.routes.append(Route(method=method.upper(), path=path, handler=handler, response_class=response_class))

    def get(self, path: str, *, response_class: Any | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route("GET", path, func, response_class)
            return func

        return decorator

    def find_route(self, method: str, path: str) -> tuple[Route, Dict[str, str]]:
        for route in self.routes:
            if route.method != method.upper():
                continue
            params = route.match(path)
            if params is not None:
                return route, params
        raise HTTPException(status_code=404, detail="Not Found")

    def handle_request(self, method: str, path: str, query_params: Dict[str, Any]) -> Any:
        route, params = self.find_route(method, path)
        arguments = {**params, **query_params}
        return route.handler(**arguments)


__all__ = ["FastAPI", "HTTPException", "Query"]
