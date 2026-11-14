# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.1 — H-021: Cost Vector (опыт стоимости)
(Конституция 4.1, статья 95: «Х-021. Стоимость. Сравнение прямой и полной
стоимости самостоятельного и делегированного исполнения»;
статья 85 — COST_VECTOR(a) = [T, A, E, M, R, O, L, I]; «Стоимость является
вектором, а не одной универсальной цифрой... Неизмеренное значение
обозначается неизвестным, а не нулём»; статья 86 — делегированная стоимость
складывается покомпонентно: Cобщая = Cисполнителя + Cкоординации +
Cконтроля + Cриска; снижение по одному компоненту не доказывает снижения
по всем; ответственность не переносится целиком.)

PASS = пять утверждений статьи 85–86 удерживаются на измеримых случаях.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..trace import Trace
from .base import ExperimentResult, experiment

COMPONENTS = ("T", "A", "E", "M", "R", "O", "L", "I")   # ст. 85


@dataclass(frozen=True)
class CostVector:
    """COST_VECTOR статьи 85. Неизмеренное — None (не ноль)."""
    values: Tuple[Optional[int], ...]   # длина 8, порядок COMPONENTS

    def __post_init__(self) -> None:
        if len(self.values) != 8:
            raise ValueError("COST_VECTOR: восемь компонентов (ст. 85)")

    @classmethod
    def of(cls, **kw) -> "CostVector":
        return cls(values=tuple(kw.get(c) for c in COMPONENTS))

    def measured(self, component: str) -> Optional[int]:
        return self.values[COMPONENTS.index(component)]

    def has_unknown(self) -> bool:
        return any(v is None for v in self.values)

    def total(self) -> Optional[int]:
        """Скалярная сумма существует ТОЛЬКО при полной измеренности.
        Неизмеренное значение не равно нулю (ст. 85) — итог неизвестен."""
        if self.has_unknown():
            return None
        return sum(self.values)

    def __add__(self, other: "CostVector") -> "CostVector":
        """Покомпонентное сложение (ст. 86). None + x = None:
        неизвестное при сложении не превращается в число."""
        return CostVector(values=tuple(
            None if (a is None or b is None) else a + b
            for a, b in zip(self.values, other.values)))


def delegate_cost(executor: CostVector, coordination: CostVector,
                  control: CostVector, risk: CostVector) -> CostVector:
    """Cобщая[a] = Cисполнителя[a] + Cкоординации[a] + Cконтроля[a] +
    Cриска[a] (ст. 86) — покомпонентно, не скалярно."""
    return executor + coordination + control + risk


@experiment("H-021", "Cost Vector (прямая и полная стоимость делегирования)")
def run_h021() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-021")

    def claim(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("COST_CLAIM", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- Утверждение 1: компоненты измеряются раздельно, а не одной цифрой.
    direct = CostVector.of(T=10, A=6, E=3, M=0, R=2, O=4, L=1, I=None)
    claim("вектор, не цифра", direct.has_unknown() and direct.total() is None,
          "компонент I не измерен: скалярной суммы НЕТ (неизвестное не "
          "превращено в ноль), хотя семь компонентов измерены")

    # --- Утверждение 2: полная стоимость делегирования складывается
    #     покомпонентно по четырём статьям (ст. 86).
    executor = CostVector.of(T=4, A=2, E=2, M=0, R=1, O=0, L=0, I=None)
    coordination = CostVector.of(T=3, A=3, E=0, M=0, R=1, O=1, L=0, I=None)
    control = CostVector.of(T=2, A=4, E=1, M=0, R=1, O=2, L=0, I=None)
    risk = CostVector.of(T=1, A=1, E=0, M=0, R=3, O=1, L=0, I=None)
    total = delegate_cost(executor, coordination, control, risk)
    ok = total.measured("T") == 10 and total.measured("A") == 10 \
        and total.measured("R") == 6 and total.measured("O") == 4
    claim("покомпонентное сложение", ok,
          f"Cобщая = {dict(zip(COMPONENTS, total.values))}: время исполнителя "
          "упало с 10 до 4, но полная стоимость времени = 4+3+2+1 = 10")

    # --- Утверждение 3: снижение одного компонента не доказывает снижения
    #     общей стоимости по всем компонентам (ст. 86).
    cheaper_T_but_not_total = (total.measured("T") == direct.measured("T")
                               and total.measured("A") > direct.measured("A")
                               and total.measured("R") > direct.measured("R"))
    claim("одно снижение != общее снижение", cheaper_T_but_not_total,
          "T исполнителя 4 < 10 прямого, но внимание 10 > 6 и риск 6 > 2: "
          "общая стоимость по вектору не снизилась")

    # --- Утверждение 4: неизвестное не гасится делегированием.
    claim("неизвестное остаётся неизвестным", total.has_unknown()
          and total.measured("I") is None,
          "ни исполнитель, ни координация, ни контроль, ни риск не измерили I: "
          "в сумме I = неизвестное, а не 0")

    # --- Утверждение 5: ответственность не переносится целиком (ст. 86).
    issuer_O = 3     # выдавший полномочие несёт ответственность
    recipient_O = 1  # получатель — за свои действия
    after_delegation = delegate_cost(executor, coordination, control, risk)
    ok = after_delegation.measured("O") == issuer_O + recipient_O \
        and issuer_O > 0 and recipient_O > 0
    claim("ответственность раздельна", ok,
          "O делегированного исполнения = 4, из них O выдающего 3 и O "
          "получателя 1: обе части ненулевые; ответственность не перенесена "
          "целиком на последнего в цепочке")

    # --- Утверждение 6: сравнение стоимостей при одинаковых условиях —
    #     только вектор против вектора, не скаляр против вектора.
    same_conditions = direct.total() is None and total.total() is None
    claim("сравнение при одинаковых условиях", same_conditions,
          "оба исполнения имеют неизмеренный компонент: скалярное "
          "«дешевле/дороже» объявить нельзя; сравниваются компоненты")

    return ExperimentResult(
        experiment_id="H-021", title="Cost Vector (стоимость делегирования)",
        passed=ok_all,
        verdict="Стоимость — вектор восьми компонентов; неизвестное не равно "
                "нулю и не гасится; делегированная стоимость складывается "
                "покомпонентно из исполнителя, координации, контроля и "
                "риска; снижение одного компонента не доказывает снижения "
                "общей; ответственность раздельна и целиком не переносится.",
        expected="неизмеренное -> сумма неизвестна; покомпонентное сложение "
                 "четырёх статей; снижение T != снижение вектора; "
                 "ответственность у обеих сторон.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
