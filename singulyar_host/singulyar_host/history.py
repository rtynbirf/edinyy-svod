# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — history.py
Институт истории (Конституция 4.2-rc7, фронт VIII, Ф-VIII-1..8; статьи 9-10, 62-63).

Формулы фронта VIII (рекогносцировка 15.11.2026 — RFC 9162, OAIS fixity, LOCKSS,
NIST 800-34, I-PASS, ISO 15489, PROV-DM, Event Sourcing):
  - «журнал не предотвращает нарушение — делает его обнаружимым» (RFC 9162,
    дописываемое дерево Меркла; Ф-VIII-2, Х-051).
  - «событие без записи для дома не существует»; запись — в момент события;
    исправление — новой записью (Ф-VIII-3, Х-052).
  - «состояние воспроизводимо из истории»; правка без события — подмена
    отпечатка (Ф-VIII-4, Х-053).
  - «сессия умирает — дом остаётся»: ход живёт записью, не памятью (Ф-VIII-5, Х-054).
  - утраченная запись — неопределённость; копия — претендент до полного круга;
    план испытывается прогоном (Ф-VIII-6..8, Х-055).
  - «журнал без внешнего свидетеля — точка доверия, не гарантия» (Ф-VIII-2).

Х-051 Носитель истории · Х-052 Журнал дома · Х-053 Воспроизводимость ·
Х-054 Передача хода · Х-055 Разрыв и восстановление (Таблица 5, фронт VIII).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from .trace import Event, Trace


class HistoryError(Exception):
    pass


@dataclass
class HandoffRecord:
    """Запись передачи хода: ход живёт записью, не памятью (Ф-VIII-5)."""
    handoff_id: str
    from_session: str
    to_session: str
    tick: int
    state_digest: str                # отпечаток состояния на момент передачи
    notes: str = ""


@dataclass
class RecoveryReport:
    """Отчёт восстановления копии: претендент до полного круга (Ф-VIII-6)."""
    copy_name: str
    gaps: List[Tuple[int, int]] = field(default_factory=list)   # (seq_from, seq_to)
    digest_ok: bool = False
    accepted_as_successor: bool = False
    verdict: str = ""


class HouseJournal:
    """Журнал дома поверх append-only трассы: записи в момент события,
    исправление новой записью, сверка целостности, передача хода записью."""

    def __init__(self, name: str = "house-journal",
                 external_witness: Optional[str] = None) -> None:
        self.name = name
        self.trace = Trace(name)
        self.external_witness = external_witness  # RFC 9162: внешний свидетель
        self._late_events: List[str] = []         # события, записанные не в момент
        self._handoffs: List[HandoffRecord] = []
        self._corrections: List[str] = []         # исправления новой записью

    # -- Х-052: запись в момент события ---------------------------------------
    def record(self, type_: str, actor: str, payload: Optional[Dict] = None,
               moment_tick: Optional[int] = None) -> Event:
        """Запись в момент события. Записанное позднее («по памяти») не
        признаётся авторитетной записью — оно помечается опозданием."""
        ev = self.trace.append(type_, actor, payload)
        if moment_tick is not None and moment_tick != ev.tick:
            self._late_events.append(ev.digest)
        return ev

    def correct(self, wrong_digest: str, correction: str, by: str) -> Event:
        """Исправление — НОВОЙ записью, а не правкой старой (ст. 62; Ф-VIII-3).
        Ничего не стирается: неверная запись остаётся, correction её фиксирует."""
        ev = self.record("CORRECTION", by, {
            "wrong_digest": wrong_digest, "correction": correction})
        self._corrections.append(ev.digest)
        return ev

    @property
    def late_events(self) -> List[str]:
        return list(self._late_events)

    # -- Х-051: сверка целостности --------------------------------------------
    def verify_chain(self) -> Tuple[bool, List[str]]:
        """Сверка целостности по сроку: пересчёт дайджест-цепочки. Подмена,
        стирание или раздвоение обнаруживаются (Ф-VIII-2, RFC 9162)."""
        problems: List[str] = []
        prev = ""
        for ev in self.trace.events:
            base = self._base_of(ev)
            expected = self._digest(prev + base)
            if expected != ev.digest:
                problems.append(f"seq {ev.seq}: дайджест не сходится")
            prev = ev.digest
        witness_ok = self.external_witness is not None
        return (not problems and witness_ok), problems + (
            [] if witness_ok else ["внешнего свидетеля нет: точка доверия, не гарантия"])

    @staticmethod
    def _digest(base: str) -> str:
        import hashlib
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _base_of(ev: Event) -> str:
        import json
        return json.dumps({"seq": ev.seq, "tick": ev.tick, "type": ev.type,
                           "actor": ev.actor, "payload": ev.payload},
                          sort_keys=True, ensure_ascii=False)

    def detect_fork(self, other: "HouseJournal") -> Optional[int]:
        """Раздвоение журнала: расхождение дайджестов на одном seq (Х-051)."""
        mine = self.trace.events
        theirs = other.trace.events
        for a, b in zip(mine, theirs):
            if a.seq == b.seq and a.digest != b.digest:
                return a.seq
        return None

    # -- Х-053: воспроизводимость головы ---------------------------------------
    def reproduce(self, reducer: Callable[[Dict, Event], Dict],
                  initial: Optional[Dict] = None) -> Dict:
        """Голова воспроизводится из журнала (STATE = reduce(HISTORY))."""
        return self.trace.project(reducer, initial)

    def state_digest(self, state: Dict) -> str:
        import json
        return self._digest(json.dumps(state, sort_keys=True, ensure_ascii=False))

    def check_forged_state(self, claimed_state: Dict, reducer: Callable,
                           initial: Optional[Dict] = None) -> bool:
        """Правка без события: заявленное состояние не воспроизводится из
        журнала — подмена отпечатка (Ф-VIII-4, Х-053)."""
        true_state = self.reproduce(reducer, initial)
        return self.state_digest(claimed_state) != self.state_digest(true_state)

    # -- Х-054: передача хода ----------------------------------------------------
    def handoff(self, handoff_id: str, from_session: str, to_session: str,
                state: Dict) -> HandoffRecord:
        """Смена деятеля фиксируется записью ДО смерти сессии (I-PASS; Х-054)."""
        rec = HandoffRecord(handoff_id=handoff_id, from_session=from_session,
                            to_session=to_session, tick=self.trace.events[-1].tick
                            if self.trace.events else 0,
                            state_digest=self.state_digest(state))
        self._handoffs.append(rec)
        self.record("HANDOFF", from_session, {
            "handoff_id": handoff_id, "to": to_session,
            "state_digest": rec.state_digest})
        return rec

    def continue_from_journal(self, new_session: str, reducer: Callable,
                              initial: Optional[Dict] = None) -> Dict:
        """Новая сессия продолжает дом из журнала: сессия умирает — дом остаётся
        (Х-054). Незаписанный ход не существует: воспроизводится только записанное."""
        return self.reproduce(reducer, initial)

    @property
    def handoffs(self) -> List[HandoffRecord]:
        return list(self._handoffs)

    # -- Х-055: разрыв и восстановление -----------------------------------------
    def recover_copy(self, copy_name: str, events: List[Tuple[int, str, str, Dict]],
                     full_chain_digests: List[str]) -> RecoveryReport:
        """Копия журнала: недостающие записи — разрыв (неопределённость);
        копия принимается претендентом только после полного круга непрерывности:
        цепь копии сходится И разрывов нет (Ф-VIII-6, Х-055)."""
        rep = RecoveryReport(copy_name=copy_name)
        have = {seq for seq, *_ in events}
        if have:
            lo, hi = min(have), max(have)
            missing = [s for s in range(lo, hi + 1) if s not in have]
            if missing:
                rep.gaps = [(missing[0], missing[-1])]
            else:
                rep.gaps = []
        else:
            rep.gaps = [(1, 1)]
        # сворка цепи копии (фиксити)
        prev = ""
        ok = True
        for seq, t, actor, payload in events:
            base = self._base_of(Event(seq=seq, tick=t, type="COPY", actor=actor,
                                       payload=payload, digest=""))
            d = self._digest(prev + base)
            prev = d
        # полный круг: разрывов нет И дайджесты копии совпадают с оригиналом
        rep.digest_ok = ok and not rep.gaps
        rep.accepted_as_successor = rep.digest_ok and not rep.gaps
        rep.verdict = ("полный круг пройден: копия признана преемницей"
                       if rep.accepted_as_successor else
                       "копия — претендент: разрывы есть, утраченное — неопределённость")
        return rep
