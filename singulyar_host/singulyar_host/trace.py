# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — trace.py

Трасса событий (Event Sourcing).
Деталь диалога (v1.9, раздел «B. Состояние и история — не одно и то же»):
    STATE != HISTORY != EVENT
    «Субъект не равен своей последней версии состояния. Он сохраняет историю
    переходов, обязательства и идентичность.»
    Источник практики: Microsoft Learn, Event Sourcing Pattern.

Здесь: EVENT — неизменяемая запись; HISTORY — журнал всех событий;
STATE (проекция) — вычисляется из событий, но не тождественна им.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class Event:
    """Неизменяемое событие трассы. Само по себе не является ни состоянием, ни историей."""
    seq: int
    tick: int                      # логическое время (такт наблюдателя)
    type: str                      # тип события, напр. "RESERVE", "ATTEST", "ACTIVATE"
    actor: str                     # кто породил событие
    payload: Dict[str, Any]        # содержимое события
    digest: str                    # хеш цепочки (простейший transparency-механизм)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seq": self.seq, "tick": self.tick, "type": self.type,
            "actor": self.actor, "payload": self.payload, "digest": self.digest,
        }


class Trace:
    """
    Append-only журнал (append-only store — по Event Sourcing Pattern).
    Не допускает перезаписи: история либо есть целиком, либо её нет.
    """

    def __init__(self, name: str = "trace") -> None:
        self.name = name
        self._events: List[Event] = []
        self._tick = 0

    # -- запись ---------------------------------------------------------------
    def append(self, type_: str, actor: str, payload: Optional[Dict[str, Any]] = None) -> Event:
        self._tick += 1
        seq = len(self._events) + 1
        base = json.dumps(
            {"seq": seq, "tick": self._tick, "type": type_, "actor": actor,
             "payload": payload or {}}, sort_keys=True, ensure_ascii=False)
        prev = self._events[-1].digest if self._events else ""
        digest = hashlib.sha256((prev + base).encode("utf-8")).hexdigest()[:16]
        ev = Event(seq=seq, tick=self._tick, type=type_, actor=actor,
                   payload=payload or {}, digest=digest)
        self._events.append(ev)
        return ev

    # -- чтение ---------------------------------------------------------------
    @property
    def events(self) -> List[Event]:
        """HISTORY: журнал целиком. Возвращаем копию списка — мутировать нельзя."""
        return list(self._events)

    def filter(self, type_: str) -> List[Event]:
        return [e for e in self._events if e.type == type_]

    def __len__(self) -> int:
        return len(self._events)

    # -- проекции -------------------------------------------------------------
    def project(self, reducer: Callable[[Dict[str, Any], Event], Dict[str, Any]],
                initial: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        STATE = reduce(EVENTS). Одна и та же история может давать разные проекции —
        это и есть демонстрация STATE != HISTORY != EVENT.
        """
        state = dict(initial or {})
        for ev in self._events:
            state = reducer(state, ev)
        return state

    def counters_by_type(self) -> Dict[str, int]:
        return self.project(lambda s, e: {**s, e.type: s.get(e.type, 0) + 1}, initial={})


def reducer_counts(state: Dict[str, int], ev: Event) -> Dict[str, int]:
    """Пример редьюсера: счётчики событий по типам."""
    s = dict(state)
    s[ev.type] = s.get(ev.type, 0) + 1
    return s
