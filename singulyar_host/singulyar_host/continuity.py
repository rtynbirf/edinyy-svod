# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — continuity.py

CONTINUITY как проверяемое ОТНОШЕНИЕ между версиями субъекта, его историей
и обязательствами (v2.1: «CONTINUITY — не свойство одного объекта»).

Continuity Vector C=(L,K,O,A,B) (v2.1, раздел «Моё решение: Continuity Vector»):
  L — Lineage: происхождение и цепочка продолжения;
  K — Causal continuity: причинная связь между состояниями;
  O — Obligations: сохранение обязательств и ответственности;
  A — Authority: законность передачи полномочий;
  B — Boundary: сохранение границ идентичности и независимости.
+ ACT (v2.2/v2.3): Activation — явное принятие перехода как авторитетного.

«Это не пять баллов, которые можно сложить... Это пять независимых проверок.
Их результаты могут быть PASS, FAIL, UNKNOWN, CONTESTED.» (v2.1)

Четыре ситуации v2.1 (дословные названия):
  A. Развитие   — возможна непрерывность
  B. Перенос    — возможна непрерывность
  C. Разветвление — «один идентификатор на двоих недостаточен»
  D. Замещение  — «сходство не доказывает непрерывность»
И девизы v2.3: IDENTICAL_STATE ⇏ IDENTICAL_SUBJECT; SAME_ID ⇏ SAME_CONTINUITY.

Честное разграничение (v2.1): техническая непрерывность идентичности НЕ решает
философский вопрос о тождестве личности — фиксируем это в результатах.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .ontology import Subject, Verdict


@dataclass(frozen=True)
class ContinuityCheck:
    lineage: str                 # тип проверки: DEVELOPMENT/MIGRATION/FORK/REPLACEMENT
    vector: Dict[str, Verdict]   # L,K,O,A,B,ACT
    overall: Verdict
    note: str = ""

    def as_dict(self) -> Dict[str, str]:
        d = {k: v.value for k, v in self.vector.items()}
        d["OVERALL"] = self.overall.value
        return d


def _vec(L: Verdict, K: Verdict, O: Verdict, A: Verdict, B: Verdict,
         ACT: Verdict) -> Dict[str, Verdict]:
    return {"L": L, "K": K, "O": O, "A": A, "B": B, "ACT": ACT}


def continuity_vector(parent: Subject, candidate: Subject,
                      kind: str,
                      activation_granted: Optional[bool] = None,
                      obligations_transferred: bool = True,
                      authorized_transfer: bool = True) -> ContinuityCheck:
    """
    Оценивает непрерывность между parent и candidate для четырёх ситуаций.
    kind in {DEVELOPMENT, MIGRATION, FORK, REPLACEMENT}.
    Проверки независимы: ни одна не выводится из другой.
    """
    # L: есть ли признанная цепочка продолжения.
    if kind == "REPLACEMENT":
        L = Verdict.FAIL          # нет признанной цепочки продолжения
    elif candidate.lineage == parent.lineage:
        L = Verdict.PASS
    else:
        L = Verdict.FAIL

    # K: причинная связь между состояниями.
    if kind == "REPLACEMENT":
        K = Verdict.UNKNOWN       # поведенческое сходство не доказывает причину
    else:
        K = Verdict.PASS if candidate.state_hash else Verdict.UNKNOWN

    # O: сохранение обязательств и ответственности.
    if kind == "REPLACEMENT" or not obligations_transferred:
        O = Verdict.FAIL
    else:
        O = Verdict.PASS if parent.commitments == candidate.commitments or \
            candidate.commitments else Verdict.UNKNOWN

    # A: законность передачи полномочий.
    if kind == "REPLACEMENT":
        A = Verdict.FAIL
    elif kind == "FORK":
        A = Verdict.CONTESTED   # два продолжения претендуют на полномочия
    else:
        A = Verdict.PASS if authorized_transfer else Verdict.CONTESTED

    # B: сохранение границ идентичности и независимости.
    if kind == "FORK":
        B = Verdict.CONTESTED     # два продолжения претендуют на одну границу
    elif kind == "REPLACEMENT":
        B = Verdict.FAIL
    else:
        B = Verdict.PASS

    # ACT: явное принятие авторитетного состояния.
    if activation_granted is True:
        ACT = Verdict.PASS
    elif activation_granted is False:
        ACT = Verdict.FAIL
    else:
        ACT = Verdict.UNKNOWN

    # Итог: непрерывность установлена только если НИ ОДНА проверка не провалена
    # и ACT получен. CONTESTED-координаты делают итог CONTESTED.
    verdicts = list(_vec(L, K, O, A, B, ACT).values())
    if Verdict.FAIL in verdicts:
        overall = Verdict.FAIL
    elif Verdict.CONTESTED in verdicts:
        overall = Verdict.CONTESTED
    elif Verdict.UNKNOWN in verdicts:
        overall = Verdict.UNKNOWN
    else:
        overall = Verdict.PASS

    notes = {
        "DEVELOPMENT": "A. Развитие: сохранены история, ответственность, "
                       "обязательства — возможна непрерывность (v2.1).",
        "MIGRATION": "B. Перенос: субстрат сменился, старый экземпляр прекращён, "
                     "цепочка продолжения признана — возможна непрерывность (v2.1).",
        "FORK": "C. Разветвление: два продолжения с одинаковой памятью и историей; "
                "один идентификатор на двоих недостаточен (v2.1). "
                "SAME_ID не доказывает SAME_CONTINUITY (v2.3).",
        "REPLACEMENT": "D. Замещение: полное поведенческое сходство без доказанной "
                       "истории — непрерывность не установлена (v2.1).",
    }
    note = notes.get(kind, "")
    if kind in ("DEVELOPMENT", "MIGRATION") and overall == Verdict.PASS:
        note += " Техническая непрерывность установлена; философский вопрос о " \
                "тождестве личности остаётся открытым (v2.1, честное разграничение)."
    return ContinuityCheck(lineage=kind, vector=_vec(L, K, O, A, B, ACT),
                           overall=overall, note=note)
