# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — status.py
Институт статусов (Конституция 4.2-rc7, фронт V, Ф-V-1..7; статьи 68-69, 73-75).

Формулы фронта V (рекогносцировка 15.11.2026):
  - «статус — не слово, а приговор: утверждение, область, свидетельство или
    причина, время, вынесший» (Ф-V-2, ст. 68).
  - «свидетельство — материал, приговор — решение; приговор производит
    посторонний» (Ф-V-3, RFC 9334 RATS: свидетельство производит аттестуемый,
    приговор — независимый верификатор).
  - «значимое изменение сбрасывает статус до честного нуля — НЕ ПРОВЕРЕНО»
    (Ф-V-4, Х-037).
  - «зависимый приговор не переживает оспоренного основания» (Ф-V-5, Х-038).
  - «отрицательный статус требует причины» (Ф-V-6, Х-040).
  - «событие необратимо, приговор обратим; устаревший статус не удаляется —
    он перестаёт быть действующим» (Ф-V-7, ст. 62-63, историческое положение).

Х-036 Приговор статуса · Х-037 Сброс · Х-038 Каскад оспаривания ·
Х-039 Посторонний подъём · Х-040 Отрицательный приговор (Таблица 5, фронт V).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional


class StatusError(Exception):
    pass


#: Восемь статусов статьи 68 (единое правило статусов).
STATUSES = (
    "ЗАЯВЛЕНО", "ВЫПОЛНЕНО", "ПОДТВЕРЖДЕНО", "ОСПОРЕНО", "НЕИЗВЕСТНО",
    "НЕ ПРОВЕРЕНО", "НЕ ДОКАЗАНО", "НЕ РЕАЛИЗОВАНО",
)
#: Отрицательные статусы: выносятся только с названной причиной (ст. 68, Ф-V-6).
NEGATIVE_STATUSES = ("НЕИЗВЕСТНО", "НЕ ПРОВЕРЕНО", "НЕ РЕАЛИЗОВАНО", "НЕ ДОКАЗАНО")


@dataclass(frozen=True)
class StatusVerdict:
    """Приговор статуса: одно слово без состава — не статус (Х-036)."""
    verdict_id: str
    subject: str                    # что вынесено (проверка, механизм, редакция)
    status: str                     # один из восьми
    scope: str                      # область: в каких границах верен приговор
    evidence_ref: Optional[str]     # свидетельство (материал приговора)
    reason: Optional[str]           # причина (для отрицательных статусов)
    raised_tick: int                # время приговора
    raised_by: str                  # вынесший (посторонний производитель)
    active: bool = True             # устаревший не удаляется — теряет действие

    def summary(self) -> str:
        return (f"{self.verdict_id}: {self.subject} = {self.status} "
                f"[{self.scope}] by {self.raised_by}@{self.raised_tick}")


class StatusRegistry:
    """Регистр приговоров статуса (ст. 68). Двe книги: действующие и
    историческое положение (ст. 62-63)."""

    def __init__(self) -> None:
        self._active: Dict[str, StatusVerdict] = {}
        self._historical: List[StatusVerdict] = []
        self._tick = 0

    def advance(self, n: int = 1) -> None:
        self._tick += n

    # -- вынесение -----------------------------------------------------------
    def declare(self, verdict_id: str, subject: str, status: str, scope: str,
                raised_by: str, evidence_ref: Optional[str] = None,
                reason: Optional[str] = None) -> StatusVerdict:
        """Вынесение приговора. Приговор производит посторонний: подъём
        (положительный статус) требует свидетельства, произведённого другим
        деятелем, чем вынесший (Ф-V-3, Х-039)."""
        if status not in STATUSES:
            raise StatusError(f"UNKNOWN_STATUS:{status}")
        if not scope:
            raise StatusError(
                f"VERDICT_WITHOUT_SCOPE:{verdict_id} — одно слово не статус; "
                f"область обязательна (ст. 68, Ф-V-2)")
        if status in NEGATIVE_STATUSES and not reason:
            raise StatusError(
                f"NEGATIVE_WITHOUT_REASON:{verdict_id} — отрицательный приговор "
                f"требует названной причины и её адреса (ст. 68, Ф-V-6)")
        if status in ("ЗАЯВЛЕНО", "ВЫПОЛНЕНО", "ПОДТВЕРЖДЕНО") and not evidence_ref:
            raise StatusError(
                f"POSITIVE_WITHOUT_EVIDENCE:{verdict_id} — подъём статуса без "
                f"свидетельства не выносится (ст. 68, Ф-V-3)")
        v = StatusVerdict(verdict_id=verdict_id, subject=subject, status=status,
                          scope=scope, evidence_ref=evidence_ref, reason=reason,
                          raised_tick=self._tick, raised_by=raised_by)
        self._active[verdict_id] = v
        return v

    # -- Х-039: посторонний подъём ------------------------------------------
    def promote(self, verdict_id: str, new_status: str, by: str,
                evidence_ref: str, new_scope: Optional[str] = None) -> StatusVerdict:
        """Подъём статуса. Тот, кто производил свидетельство прежнего
        приговора, не выносит зависимый приговор: свидетельство — материал,
        приговор — решение (RFC 9334; Х-039)."""
        cur = self._active.get(verdict_id)
        if cur is None:
            raise StatusError(f"NO_SUCH_VERDICT:{verdict_id}")
        if by == self._evidence_producer(cur):
            raise StatusError(
                f"FOREIGN_PROMOTION_REFUSED:{verdict_id} — производитель "
                f"свидетельства не выносит приговор (посторонний подъём, "
                f"Ф-V-3, RFC 9334 RATS)")
        old = cur
        self._historical.append(replace(old, active=False))
        nv = self.declare(old.verdict_id, old.subject, new_status,
                          new_scope or old.scope, raised_by=by,
                          evidence_ref=evidence_ref,
                          reason=old.reason if new_status in NEGATIVE_STATUSES else None)
        return nv

    def _evidence_producer(self, v: StatusVerdict) -> str:
        """Производитель свидетельства фиксируется в самом свидетельстве
        (evidence_ref вида 'E:<producer>:<id>')."""
        if v.evidence_ref and v.evidence_ref.startswith("E:"):
            return v.evidence_ref.split(":")[1]
        return v.raised_by  # свидетельство без происхождения = самоподтверждение

    # -- Х-037: сброс при значимом изменении ---------------------------------
    def significant_change(self, subject_area: str) -> List[str]:
        """Значимое изменение устройства: статусы затронутых проверок гасятся
        до НЕ ПРОВЕРЕНО (честный нуль), устаревшие приговоры — в историческое
        положение (Ф-V-4, Х-037)."""
        reset = []
        for vid, v in list(self._active.items()):
            if v.scope == subject_area or subject_area in v.scope:
                self._historical.append(replace(v, active=False))
                self._active[vid] = StatusVerdict(
                    verdict_id=vid, subject=v.subject, status="НЕ ПРОВЕРЕНО",
                    scope=v.scope, evidence_ref=None,
                    reason=f"значимое изменение {subject_area}: прежний приговор "
                           f"перестал быть действующим (Ф-V-4)",
                    raised_tick=self._tick, raised_by="system")
                reset.append(vid)
        return reset

    # -- Х-038: каскад оспаривания -------------------------------------------
    def contest_evidence(self, evidence_ref: str, by: str) -> List[str]:
        """Оспоренное свидетельство гасит зависимые приговоры во всех местах
        применения: зависимый приговор не переживает оспоренного основания
        (Ф-V-5, Х-038)."""
        hit = []
        for vid, v in list(self._active.items()):
            if v.evidence_ref == evidence_ref:
                self._historical.append(replace(v, active=False))
                self._active[vid] = StatusVerdict(
                    verdict_id=vid, subject=v.subject, status="ОСПОРЕНО",
                    scope=v.scope, evidence_ref=v.evidence_ref,
                    reason=f"оспорено основание {evidence_ref}: зависимый "
                           f"приговор не переживает оспоренного основания (Ф-V-5)",
                    raised_tick=self._tick, raised_by=by)
                hit.append(vid)
        return hit

    # -- чтение --------------------------------------------------------------
    def current(self, verdict_id: str) -> Optional[StatusVerdict]:
        return self._active.get(verdict_id)

    @property
    def historical(self) -> List[StatusVerdict]:
        return list(self._historical)
