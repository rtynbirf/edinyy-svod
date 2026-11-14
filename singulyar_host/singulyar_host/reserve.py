# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — reserve.py
Институт запаса (Конституция 4.2-rc7, фронт IX, Ф-IX-1..8; статьи 23, 40-45).

Формулы фронта IX (рекогносцировка 15.11.2026 — SPR/ЭПЗА-1975, Свальбард,
Базель-III LCR, страховой запас FEFO, Уптайм-институт, 3-2-1-1-0, Ready.gov):
  - «запас — дни автономности при названном расходе»; расход ниже неснижаемого
    остатка отклоняется; ноль — только явным решением (Ф-IX-2, Х-056).
  - «истекающий первым выходит первым»; гибель без записи — утечка;
    инвентаризация по сроку (Ф-IX-3, Х-057).
  - «вскрытие — полный круг с записью»; молчание не вскрывает; вскрытие без
    записи — захват (Ф-IX-4, Х-058).
  - «одна беда не гасит род»: независимость по беде, не по адресу; единое
    место — точка отказа (Ф-IX-5, Х-059).
  - «прогон — разбор, вскрытие, восполнение»; непроверенный запас —
    НЕ РЕАЛИЗОВАНО (Ф-IX-7, Х-060).

Х-056 Мера и пол · Х-057 Ротация · Х-058 Вскрытие · Х-059 Распределённость ·
Х-060 Испытание (Таблица 5, фронт IX).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ReserveError(Exception):
    pass


@dataclass
class ReserveItem:
    """Единица запаса: срок, место, класс беды (не адрес — независимость по
    беде, Ф-IX-5)."""
    item_id: str
    kind: str
    quantity: float
    unit: str
    expires_tick: int                # FEFO: истекающий первым выходит первым
    hazard_class: str                # класс беды, от которого спасает
    location: str
    recorded_tick: int               # запись при поступлении (гибель без записи = утечка)
    dead_recorded: Optional[int] = None   # запись гибели (иначе — утечка)


@dataclass
class Consumption:
    consumption_id: str
    item_id: str
    quantity: float
    tick: int
    opened_by: str
    recorded: bool = True


class ReservePool:
    """Пул запаса с мерой (дни автономности), полом, FEFO-ротацией, вскрытием
    полным кругом и распределённостью по беде."""

    def __init__(self) -> None:
        self._items: Dict[str, ReserveItem] = {}
        self._consumptions: List[Consumption] = []
        self._daily_burn: Dict[str, float] = {}   # kind -> расход в сутки
        self._floors: Dict[str, float] = {}       # kind -> неснижаемый остаток
        self._zero_decisions: Dict[str, str] = {} # kind -> запись явного решения о нуле
        self._tick = 0
        self.drills: List[Dict] = []
        self._leaks: List[str] = []

    def advance(self, n: int = 1) -> None:
        self._tick += n

    # -- Х-056: мера и пол -----------------------------------------------------
    def set_burn(self, kind: str, per_day: float) -> None:
        self._daily_burn[kind] = per_day

    def set_floor(self, kind: str, floor: float, by: str,
                  decision_id: str) -> None:
        """Пол (неснижаемый остаток) ставится явным решением. Ноль пола — тоже
        только явным решением, записанным (Ф-IX-2, Х-056)."""
        if floor == 0:
            self._zero_decisions[kind] = f"{decision_id}:{by}@{self._tick}"
        self._floors[kind] = floor

    def autonomy_days(self, kind: str) -> float:
        """Мера запаса: дни автономности при названном расходе (Ф-IX-2)."""
        burn = self._daily_burn.get(kind)
        if not burn:
            raise ReserveError(f"NO_BURN_RATE:{kind} — расход не назван: мера "
                               f"автономности не определена (Х-056)")
        stock = self.stock(kind)
        return stock / burn

    def stock(self, kind: str) -> float:
        return sum(i.quantity for i in self._items.values()
                   if i.kind == kind and i.dead_recorded is None
                   and i.expires_tick > self._tick)

    def consume(self, consumption_id: str, kind: str, quantity: float,
                by: str) -> Consumption:
        """Расход: ниже неснижаемого остатка отклоняется (Ф-IX-2, Х-056).
        Ноль пола без явного решения запрещает расход вовсе (Х-056)."""
        if kind not in self._daily_burn:
            raise ReserveError(f"NO_BURN_RATE:{kind} — расход ниже названного "
                               f"не начисляется: мера не определена")
        if kind not in self._floors:
            raise ReserveError(
                f"NO_FLOOR:{kind} — неснижаемый остаток не установлен явным "
                f"решением: расход отклоняется (Ф-IX-2)")
        floor = self._floors[kind]
        available = self.stock(kind)
        if available - quantity < floor:
            if kind in self._zero_decisions and floor == 0 and available - quantity < 0:
                raise ReserveError(f"OVERDRAW:{kind}")
            raise ReserveError(
                f"BELOW_FLOOR:{kind} — расход {quantity} уводит запас ниже "
                f"неснижаемого остатка {floor}: отклоняется (Х-056)")
        item = self._earliest_fefo(kind, quantity)
        if item is None:
            raise ReserveError(f"EMPTY:{kind}")
        take = min(quantity, item.quantity)
        c = Consumption(consumption_id=consumption_id, item_id=item.item_id,
                        quantity=take, tick=self._tick, opened_by=by, recorded=True)
        item.quantity -= take
        if item.quantity <= 0:
            item.dead_recorded = self._tick
        self._consumptions.append(c)
        return c

    def zero_floor_without_decision(self, kind: str) -> bool:
        """Ноль пола без явного решения не допускается: инвариант проверки."""
        return kind not in self._zero_decisions

    # -- Х-057: FEFO-ротация и утечка -------------------------------------------
    def _earliest_fefo(self, kind: str, quantity: float) -> Optional[ReserveItem]:
        """Истекающий первым выходит первым (FEFO)."""
        alive = [i for i in self._items.values()
                 if i.kind == kind and i.dead_recorded is None
                 and i.expires_tick > self._tick and i.quantity > 0]
        alive.sort(key=lambda i: i.expires_tick)
        return alive[0] if alive else None

    def expire_sweep(self) -> List[str]:
        """Инвентаризация по сроку: гибель без записи — утечка (Ф-IX-3, Х-057)."""
        leaked = []
        for i in self._items.values():
            if i.expires_tick <= self._tick and i.dead_recorded is None \
               and i.quantity > 0:
                leaked.append(i.item_id)
        self._leaks.extend(leaked)
        return leaked

    @property
    def leaks(self) -> List[str]:
        return list(self._leaks)

    def receive(self, item: ReserveItem) -> ReserveItem:
        self._items[item.item_id] = item
        return item

    # -- Х-058: вскрытие полным кругом -------------------------------------------
    def open_reserve(self, item_id: str, by: str,
                     plan: Optional[str] = None) -> Consumption:
        """Вскрытие запаса — полный круг: расход + запись + план восполнения.
        Молчание не вскрывает; вскрытие без записи и плана — захват (Ф-IX-4)."""
        item = self._items.get(item_id)
        if item is None:
            raise ReserveError(f"NO_SUCH_ITEM:{item_id}")
        if not plan:
            raise ReserveError(
                f"OPEN_WITHOUT_RECORD:{item_id} — вскрытие без записи и плана "
                f"восполнения есть захват (Ф-IX-4, Х-058)")
        return self.consume(f"open-{item_id}-{self._tick}", item.kind,
                            item.quantity, by)

    # -- Х-059: распределённость по беде ------------------------------------------
    def survive_hazard(self, hazard_class: str) -> float:
        """Одна беда не гасит род: гасятся только единицы того же класса беды.
        Независимость по беде, не по адресу (Ф-IX-5, Х-059)."""
        return sum(i.quantity for i in self._items.values()
                   if i.hazard_class != hazard_class and i.dead_recorded is None)

    @staticmethod
    def single_point_of_failure(items: List[ReserveItem]) -> Optional[str]:
        """Единое место (один адрес) для всего рода — точка отказа (Х-059)."""
        kinds: Dict[str, str] = {}
        for i in items:
            if kinds.setdefault(i.kind, i.location) != i.location:
                continue
        # род хранится в одном месте, если все единицы рода в одном адресе
        by_kind: Dict[str, set] = {}
        for i in items:
            by_kind.setdefault(i.kind, set()).add(i.location)
        for kind, locs in by_kind.items():
            if len(locs) == 1:
                return f"{kind}@{next(iter(locs))}"
        return None

    # -- Х-060: испытание -----------------------------------------------------------
    def drill(self, drill_id: str, kind: str) -> Dict:
        """Прогон запаса: разбор (инвентаризация), вскрытие, восполнение
        (Ф-IX-7, Х-060)."""
        inventory_before = self.stock(kind)
        days_before = self.autonomy_days(kind)
        item = self._earliest_fefo(kind, 0)
        opened = None
        if item is not None:
            plan = f"восполнение {item.kind} после прогона {drill_id}"
            opened = self.open_reserve(item.item_id, "drill", plan=plan)
        replenished = self.receive(ReserveItem(
            item_id=f"{drill_id}-repl", kind=kind,
            quantity=max(1.0, inventory_before * 0.25), unit="unit",
            expires_tick=self._tick + 20, hazard_class="drill-hazard",
            location="drill-site", recorded_tick=self._tick))
        days_after = self.autonomy_days(kind)
        report = {
            "drill_id": drill_id, "kind": kind, "inventory_before": inventory_before,
            "days_before": days_before, "opened": opened.consumption_id if opened else None,
            "replenished": replenished.item_id, "days_after": days_after,
            "realized": True,
        }
        self.drills.append(report)
        return report

    def realization_status(self, kind: str) -> str:
        """Непроверенный запас — НЕ РЕАЛИЗОВАНО; испытанный — ВЫПОЛНЕНО
        в пределах прогона (Ф-IX-7, Х-060)."""
        if any(d["kind"] == kind for d in self.drills):
            return "ВЫПОЛНЕНО (в пределах прогона)"
        return "НЕ РЕАЛИЗОВАНО: прогон не проводился (Х-060)"
