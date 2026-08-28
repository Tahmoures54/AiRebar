# utils/events.py
"""Concurrent-safe event bus: thread-safe, Tk marshal, debounce, batch."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any, Callable, DefaultDict, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("RebarAgent.Events")
Listener = Callable[[Dict[str, Any]], None]

_COALESCE_EVENTS = frozenset({
    "ui.refresh_request", "stock.changed", "scrap.changed",
    "position.saved", "position.deleted", "cut.confirmed", "cut.rolled_back", "project.opened",
})


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subs: DefaultDict[str, List[Listener]] = defaultdict(list)
        self._history: Deque[Tuple[float, str, Dict[str, Any]]] = deque(maxlen=80)
        self._ui_root = None
        self._ui_pending: Deque[Tuple[str, Dict[str, Any]]] = deque()
        self._ui_flush_scheduled = False
        self._ui_debounce_ms = 50
        self._active_listeners: Set[int] = set()
        self._batch_depth = 0
        self._batch_queue: List[Tuple[str, Dict[str, Any]]] = []
        self.stats = {"emitted": 0, "delivered": 0, "coalesced": 0, "dropped_reentrant": 0, "ui_flushes": 0}

    def bind_ui(self, root) -> None:
        self._ui_root = root

    def unbind_ui(self) -> None:
        self._ui_root = None

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

    def once(self, event: str, listener: Listener) -> None:
        def _wrap(payload: Dict[str, Any]) -> None:
            try:
                listener(payload)
            finally:
                self.unsubscribe(event, _wrap)
        self.subscribe(event, _wrap)

    def begin_batch(self) -> None:
        with self._lock:
            self._batch_depth += 1

    def end_batch(self) -> None:
        with self._lock:
            if self._batch_depth <= 0:
                return
            self._batch_depth -= 1
            if self._batch_depth > 0:
                return
            queued = list(self._batch_queue)
            self._batch_queue.clear()
        for event, data in queued:
            self._deliver(event, data)

    def __enter__(self) -> "EventBus":
        self.begin_batch()
        return self

    def __exit__(self, *exc) -> None:
        self.end_batch()

    def emit(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        event = (event or "").strip()
        if not event:
            return
        data = dict(payload or {})
        data.setdefault("_event", event)
        data.setdefault("_ts", time.time())
        data.setdefault("_thread", threading.current_thread().name)
        with self._lock:
            self.stats["emitted"] += 1
            self._history.append((time.time(), event, data))
            if self._batch_depth > 0:
                self._batch_queue.append((event, data))
                return
        self._deliver(event, data)

    def emit_ui(self, event: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Deliver on Tk main thread; coalesce rapid refresh events."""
        event = (event or "").strip()
        data = dict(payload or {})
        data.setdefault("_event", event)
        data.setdefault("_ts", time.time())
        data.setdefault("_thread", threading.current_thread().name)
        data["_ui_marshaled"] = True
        root = self._ui_root
        if root is None:
            self.emit(event, data)
            return
        with self._lock:
            self.stats["emitted"] += 1
            self._history.append((time.time(), event, data))
            self._ui_pending.append((event, data))
            if self._ui_flush_scheduled:
                self.stats["coalesced"] += 1
                return
            self._ui_flush_scheduled = True
        try:
            root.after(self._ui_debounce_ms, self._flush_ui_queue)
        except Exception as e:
            logger.warning("UI after() failed (%s); inline", e)
            with self._lock:
                self._ui_flush_scheduled = False
            self._flush_ui_queue()

    def _flush_ui_queue(self) -> None:
        with self._lock:
            pending = list(self._ui_pending)
            self._ui_pending.clear()
            self._ui_flush_scheduled = False
            self.stats["ui_flushes"] += 1
        if not pending:
            return
        by_event: Dict[str, Dict[str, Any]] = {}
        reasons: List[str] = []
        for event, data in pending:
            if event in _COALESCE_EVENTS:
                merged = by_event.get(event, {})
                merged.update(data)
                r = data.get("reason")
                if r and str(r) not in reasons:
                    reasons.append(str(r))
                if reasons:
                    merged["reasons"] = list(reasons)
                    merged["reason"] = reasons[-1]
                by_event[event] = merged
            else:
                self._deliver(event, data)
        domain_hit = [e for e in by_event if e != "ui.refresh_request"]
        if domain_hit and "ui.refresh_request" not in by_event:
            by_event["ui.refresh_request"] = {
                "_event": "ui.refresh_request", "reason": "coalesced",
                "reasons": reasons or domain_hit, "_ui_marshaled": True,
            }
        for event, data in by_event.items():
            self._deliver(event, data)

    def _deliver(self, event: str, data: Dict[str, Any]) -> None:
        with self._lock:
            listeners = list(self._subs.get(event, []))
            listeners += list(self._subs.get("*", []))
        for fn in listeners:
            lid = id(fn)
            with self._lock:
                if lid in self._active_listeners:
                    self.stats["dropped_reentrant"] += 1
                    continue
                self._active_listeners.add(lid)
            try:
                fn(data)
                with self._lock:
                    self.stats["delivered"] += 1
            except Exception as e:
                logger.error("Listener error on '%s': %s", event, e, exc_info=True)
            finally:
                with self._lock:
                    self._active_listeners.discard(lid)

    def recent(self, n: int = 10) -> List[tuple]:
        with self._lock:
            return list(self._history)[-n:]

    def clear(self) -> None:
        with self._lock:
            self._subs.clear()
            self._history.clear()
            self._ui_pending.clear()
            self._batch_queue.clear()
            self._batch_depth = 0
            self._ui_flush_scheduled = False

    def set_debounce_ms(self, ms: int) -> None:
        self._ui_debounce_ms = max(0, int(ms))


bus = EventBus()
