# utils/events.py
"""Lightweight in-process event bus for RebarAgent UI / logic sync."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, List, Optional

logger = logging.getLogger("RebarAgent.Events")
Listener = Callable[[Dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subs: DefaultDict[str, List[Listener]] = defaultdict(list)
        self._history: List[tuple] = []
        self._history_limit = 50

    def subscribe(self, event: str, listener: Listener) -> None:
        event = (event or "").strip()
        if not event or not callable(listener):
            return
        with self._lock:
            if listener not in self._subs[event]:
                self._subs[event].append(listener)

    def unsubscribe(self, event: str, listener: Listener) -> None:
        with self._lock:
            lst = self._subs.get(event) or []
            if listener in lst:
                lst.remove(listener)

    def emit(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        event = (event or "").strip()
        data = dict(payload or {})
        data.setdefault("_event", event)
        with self._lock:
            listeners = list(self._subs.get(event, []))
            listeners += list(self._subs.get("*", []))
            self._history.append((event, data))
            if len(self._history) > self._history_limit:
                self._history = self._history[-self._history_limit :]
        for fn in listeners:
            try:
                fn(data)
            except Exception as e:
                logger.error("Listener error on '%s': %s", event, e, exc_info=True)

    def once(self, event: str, listener: Listener) -> None:
        def _wrap(payload: Dict[str, Any]) -> None:
            try:
                listener(payload)
            finally:
                self.unsubscribe(event, _wrap)
        self.subscribe(event, _wrap)

    def recent(self, n: int = 10) -> List[tuple]:
        with self._lock:
            return list(self._history[-n:])

    def clear(self) -> None:
        with self._lock:
            self._subs.clear()
            self._history.clear()


bus = EventBus()
