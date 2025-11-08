from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


class FakeTime:
    """Deterministic time/sleep for tests."""

    def __init__(self, start: float = 0.0, tick_on_time_call: float = 0.0) -> None:
        self.current = start
        self.tick_on_time_call = tick_on_time_call

    def time(self) -> float:
        self.current += self.tick_on_time_call
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += float(seconds)


class FakeResp:
    """Minimal response object with status_code, content, and json()."""

    def __init__(self, status_code: int = 200, json_data: Optional[Dict[str, Any]] = None, content: bytes = b"") -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.content = content

    def json(self) -> Dict[str, Any]:
        return dict(self._json_data or {})


class Queue:
    """Simple FIFO queue to drive sequential responses."""

    def __init__(self, items: Optional[List[Any]] = None) -> None:
        self.items: List[Any] = list(items or [])

    def push(self, item: Any) -> None:
        self.items.append(item)

    def pop(self) -> Any:
        if not self.items:
            raise IndexError("Queue empty")
        return self.items.pop(0)

    def __len__(self) -> int:  # noqa: D401
        return len(self.items)


class FakeSession:
    """Requests-like session that returns scripted responses per-URL."""

    def __init__(self) -> None:
        self.post_routes: Dict[str, Callable[..., FakeResp]] = {}
        self.get_routes: Dict[str, Queue] = {}

    # Define scripting helpers
    def script_post(self, url: str, responder: Callable[..., FakeResp]) -> None:
        self.post_routes[url] = responder

    def script_get_sequence(self, url: str, responses: List[FakeResp]) -> None:
        self.get_routes[url] = Queue(responses)

    # Implement requests-like API
    def post(self, url: str, headers: Optional[Dict[str, str]] = None, json: Optional[Dict[str, Any]] = None, timeout: int = 30) -> FakeResp:
        fn = self.post_routes.get(url)
        if fn is None:
            raise RuntimeError(f"Unexpected POST {url}")
        return fn(headers=headers, json=json, timeout=timeout)

    def get(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> FakeResp:
        if url not in self.get_routes:
            raise RuntimeError(f"Unexpected GET {url}")
        queue = self.get_routes[url]
        return queue.pop()