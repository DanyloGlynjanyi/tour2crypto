"""Testing utilities for the FastAPI shim."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from . import FastAPI, HTTPException


@dataclass
class Response:
    status_code: int
    body: Any

    def json(self) -> Any:
        return self.body

    @property
    def text(self) -> str:
        if isinstance(self.body, str):
            return self.body
        return json.dumps(self.body)


class TestClient:
    """Very small subset of starlette.testclient behaviour."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def get(self, url: str) -> Response:
        parsed = urlparse(url)
        path = parsed.path or "/"
        query_params = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        try:
            result = self.app.handle_request("GET", path, query_params)
            status_code = 200
        except HTTPException as exc:
            result = {"detail": exc.detail}
            status_code = exc.status_code
        return Response(status_code=status_code, body=result)


__all__ = ["Response", "TestClient"]
