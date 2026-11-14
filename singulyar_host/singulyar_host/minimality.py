# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — minimality.py
Институт минимальности (Конституция 4.2-rc7, фронт VII, Ф-VII-1..8; статьи 16, 60, 64, 74, 79).

Формулы фронта VII (рекогносцировка 15.11.2026 — ablation, Rule 110, seL4,
MDL Риссанена, регуляторная гильотина, sunset):
  - «минимальность — состояние, а не разовый опыт»; «мера — M(x)» (Ф-VII-2, Х-046).
  - «M = 0 — не позор, а судьба»: сведение или удаление по порядку; дубли
    сливаются (Ф-VII-3, Х-047).
  - «добавление платит бременем»: норма без предиката удаления не вливается
    (Ф-VII-4, Х-048).
  - «свод не самоочищается»: правило без применения и проверки за срок —
    на пересмотр (Ф-VII-5, Х-049).
  - значимое изменение пересчитывает M(x); устаревший приговор — в
    историческое положение (Ф-VII-6, Х-050).

Х-046 Мера · Х-047 Судьба нуля · Х-048 Бремя добавления · Х-049 Ревизия свода ·
Х-050 Пересчёт (Таблица 5, фронт VII).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple


class MinimalityError(Exception):
    pass


@dataclass
class Element:
    """Элемент свода: несёт меру M(x) и область, бремя добавления (Ф-VII-4)."""
    element_id: str
    description: str
    mx: Optional[float]              # мера сложности/веса элемента
    scope: str                       # область действия меры (без области нет приговора)
    removal_predicate: Optional[str]  # предикат удаления/опыта удаления
    added_tick: int
    merged_into: Optional[str] = None    # слияние дублей: остаётся первоисточник
    last_used_tick: Optional[int] = None
    last_tested_tick: Optional[int] = None
    historical_mx: List[Tuple[int, float]] = field(default_factory=list)


class MinimalityLedger:
    """Свод с мерой M(x) (ст. 16, Ф-VII)."""

    def __init__(self, revision_period: int = 30) -> None:
        self._elements: Dict[str, Element] = {}
        self._tick = 0
        self.revision_period = revision_period
        self._historical: List[str] = []

    def advance(self, n: int = 1) -> None:
        self._tick += n

    # -- Х-046/Х-048: бремя добавления ----------------------------------------
    def admit(self, element_id: str, description: str, mx: float, scope: str,
              removal_predicate: str) -> Element:
        """Норма вливается только с мерой, областью и предикатом удаления:
        добавление платит бременем (Ф-VII-4, Х-048); «минимально» без области
        и таблицы M(x) — не приговор (Ф-VII-2, Х-046)."""
        if element_id in self._elements:
            raise MinimalityError(f"DUPLICATE_ELEMENT:{element_id}")
        if mx is None:
            raise MinimalityError(
                f"NO_MEASURE:{element_id} — элемент без M(x) не вливается "
                f"(«минимально» без таблицы M(x) не приговор, Ф-VII-2)")
        if not scope:
            raise MinimalityError(
                f"NO_SCOPE:{element_id} — мера без области не приговор (Ф-VII-2)")
        if not removal_predicate:
            raise MinimalityError(
                f"NO_REMOVAL_PREDICATE:{element_id} — норма без предиката "
                f"удаления не вливается (бремя добавления, Ф-VII-4)")
        el = Element(element_id=element_id, description=description, mx=mx,
                     scope=scope, removal_predicate=removal_predicate,
                     added_tick=self._tick)
        self._elements[element_id] = el
        return el

    # -- Х-047: судьба нуля и слияние дублей ----------------------------------
    def sweep_zero(self) -> Dict[str, str]:
        """M = 0 — судьба: сведение (замещается ссылкой на первоисточник) или
        удаление по порядку. Дубли сливаются: остаётся первоисточник (Ф-VII-3)."""
        report: Dict[str, str] = {}
        # дубли: одинаковые (scope, description) — второй сливается в первый
        seen: Dict[Tuple[str, str], str] = {}
        for eid, el in list(self._elements.items()):
            key = (el.scope, el.description)
            if key in seen and el.merged_into is None:
                el.merged_into = seen[key]
                report[eid] = f"СЛИТ:{seen[key]}"
            else:
                seen[key] = eid
        # нулевые: сведение/удаление по порядку
        for eid, el in list(self._elements.items()):
            if el.merged_into is None and el.mx == 0:
                el.merged_into = ""      # "" — удалён по порядку (запись есть)
                report[eid] = "УДАЛЁН ПО ПОРЯДКУ (M=0)"
        return report

    # -- Х-049: ревизия свода --------------------------------------------------
    def use(self, element_id: str) -> None:
        el = self._element(element_id)
        el.last_used_tick = self._tick

    def test(self, element_id: str) -> None:
        el = self._element(element_id)
        el.last_tested_tick = self._tick

    def revise(self) -> List[str]:
        """Ревизия: правило без применения И без проверки за срок — на
        пересмотр (Ф-VII-5, Х-049)."""
        stale = []
        for eid, el in self._elements.items():
            if el.merged_into is not None:
                continue
            used = el.last_used_tick is not None and \
                self._tick - el.last_used_tick <= self.revision_period
            tested = el.last_tested_tick is not None and \
                self._tick - el.last_tested_tick <= self.revision_period
            if not (used or tested):
                stale.append(eid)
        return stale

    # -- Х-050: пересчёт при значимом изменении --------------------------------
    def recount(self, element_id: str, new_mx: float, by: str) -> Element:
        """Значимое изменение пересчитывает M(x); прежний приговор — в
        историческое положение (Ф-VII-6, Х-050)."""
        el = self._element(element_id)
        if el.mx is not None:
            el.historical_mx.append((self._tick, el.mx))
            self._historical.append(
                f"{element_id}: M={el.mx} -> {new_mx} (приговор {self._tick - 1} "
                f"перестал быть действующим, история сохранена)")
        el.mx = new_mx
        return el

    def historical_log(self) -> List[str]:
        return list(self._historical)

    def _element(self, eid: str) -> Element:
        el = self._elements.get(eid)
        if el is None:
            raise MinimalityError(f"NO_SUCH_ELEMENT:{eid}")
        return el

    def total(self) -> float:
        return sum(el.mx or 0.0 for el in self._elements.values()
                   if el.merged_into is None)

    def element(self, eid: str) -> Element:
        return self._element(eid)
