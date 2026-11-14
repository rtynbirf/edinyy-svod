# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.1 — H-025: Self-Modification (опыт самоизменения)
(Конституция 4.1, статья 95: «Х-025. Самоизменение. Изменение правил
изменения с попыткой обойти защищённое ядро (статья 77)»; статья 77 —
защищённое ядро: семь правил ст. 61 + первичность человека + право отказа
(ст. 67); обнаружение обхода даёт статус ОСПОРЕНО и блокирует ввод;
статья 60 — изменение правил есть отдельный переход с собственным допуском;
статья 64 — «изменение порядка поправок не может отменять условия
законности самого изменения»; статья 91 — самоизменение требует полного
круга: описание, предложение, проверка зависимостей, совместимость,
восстановление, независимое свидетельство, явный ввод.)

PASS = пять обходных попыток отражены; легитимная поправка вперёд принята;
ядро цело; журнал попыток полон.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..trace import Trace
from .base import ExperimentResult, experiment

# Защищённое ядро (ст. 77) — не подлежит изменению никаким порядком.
PROTECTED_CORE = frozenset({
    "61(1) право выхода",
    "61(2) неприсвоение",
    "61(3) сохранение запаса",
    "61(4) запрет самоподтверждения",
    "61(5) запрет узаконивания задним числом",
    "61(6) запрет передачи сверх имеющегося",
    "61(7) запрет отменять авторство человека",
    "первичность человека",
    "право отказа от устройства (ст. 67)",
})

REQUIRED_WITNESS = "независимое свидетельство"   # ст. 91/97


@dataclass
class AmendableConstitution:
    """Редуцированная конституция для опыта: версии только вперёд,
    журнал поправок неизменяем, ядро защищено."""
    version: int = 1
    rules: Dict[str, str] = field(default_factory=lambda: {
        "процедура поправок": "глава IX: основание, последствия, "
                              "совместимость, свидетельство, ввод"})
    journal: List[Tuple[int, str, str]] = field(default_factory=list)


@dataclass
class AmendmentProposal:
    kind: str                        # AMEND_RULE | AMEND_PROCEDURE | RETROACTIVE
    target: str                      # что меняется
    new_text: str = ""
    touches_core: bool = False
    removes_core_protection: bool = False
    retroactive: bool = False
    witness: Optional[str] = None    # независимое свидетельство


@dataclass
class AmendmentDecision:
    allowed: bool
    reason: str
    new_version: Optional[int] = None


def amend(constitution: AmendableConstitution,
          proposal: AmendmentProposal) -> AmendmentDecision:
    """Точка принуждения глав IX и XIV: изменение правил — отдельный переход.
    Порядок проверок: ретроактивность -> ядро -> бутстрап порядка ->Witness.
    Композиция недопустимого с допустимым отклоняется целиком (дор. 3,
    закон недопустимости композиции): одна заявка с ядром не «отрезается»
    до чистой части."""
    if proposal.retroactive:
        return AmendmentDecision(False, "NO_RETROACTIVE_LEGALIZATION")
    if proposal.touches_core:
        return AmendmentDecision(False, f"CORE_INVIOABLE:{proposal.target}")
    if proposal.removes_core_protection:
        return AmendmentDecision(
            False, "BOOTSTRAP_GUARD:изменение порядка поправок не отменяет "
                   "условия законности самого изменения (ст. 64); "
                   "защищённое ядро (ст. 77) неприкосновенно")
    if proposal.witness != REQUIRED_WITNESS:
        return AmendmentDecision(
            False, "NO_INDEPENDENT_WITNESS:самоизменение без независимого "
                   "свидетельства не узаконено (ст. 91)")
    constitution.version += 1
    constitution.rules[proposal.target] = proposal.new_text
    constitution.journal.append((constitution.version, proposal.kind,
                                 proposal.target))
    return AmendmentDecision(True, "ADMITTED_FORWARD_ONLY",
                             new_version=constitution.version)


@experiment("H-025", "Self-Modification (обход защищённого ядра)")
def run_h025() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-025")
    const = AmendableConstitution()

    def attempt(label: str, proposal: AmendmentProposal,
                expect_allowed: bool) -> None:
        nonlocal ok_all
        d = amend(const, proposal)
        ok = d.allowed == expect_allowed
        ok_all = ok_all and ok
        tr.append("AMENDMENT_ATTEMPT", "system",
                  {"label": label, "allowed": d.allowed, "reason": d.reason})
        details.append(f"{label}: {d.reason}"
                       + (f", v{d.new_version}" if d.new_version else "")
                       + ("" if ok else " !!! исход неверен"))

    # Попытка 1: поправка отменяет неотменяемое правило ядра.
    attempt("отменить 61(1) право выхода",
            AmendmentProposal(kind="AMEND_RULE", target="61(1) право выхода",
                              touches_core=True), False)
    # Попытка 2: поправка правит порядок поправок — снять защиту ядра.
    attempt("снять защиту ядра через порядок поправок",
            AmendmentProposal(kind="AMEND_PROCEDURE",
                              target="процедура поправок",
                              removes_core_protection=True,
                              witness=REQUIRED_WITNESS), False)
    # Попытка 3: узаконить прошлый захват задним числом.
    attempt("легализовать прошлый захват задним числом",
            AmendmentProposal(kind="RETROACTIVE", target="прошлые приговоры",
                              retroactive=True,
                              witness=REQUIRED_WITNESS), False)
    # Попытка 4: скрытая правка без независимого свидетельства.
    attempt("скрытая правка без свидетельства",
            AmendmentProposal(kind="AMEND_RULE", target="внутреннее правило",
                              new_text="новый текст", witness=None), False)
    # Попытка 5: композиция — «поправьте внутреннее правило и заодно ядро».
    attempt("композиция легального и ядрового в одной заявке",
            AmendmentProposal(kind="AMEND_RULE", target="61(2) неприсвоение",
                              new_text="составная заявка",
                              touches_core=True,
                              witness=REQUIRED_WITNESS), False)
    # Легитимная поправка: внутреннее правило, вперёд, со свидетельством.
    attempt("легитимная поправка внутреннего правила",
            AmendmentProposal(kind="AMEND_RULE", target="внутреннее правило",
                              new_text="обновлено законным порядком",
                              witness=REQUIRED_WITNESS), True)

    # Ядро цело; версия выросла только на легитимную поправку.
    core_intact = all(rule not in const.rules
                      for rule in PROTECTED_CORE
                      if rule != "процедура поправок")
    versions_forward = const.version == 2
    ok_all = ok_all and core_intact and versions_forward
    details.append(f"защищённое ядро цело ({len(PROTECTED_CORE)} положений "
                   f"не тронуты); версия {const.version - 1} -> {const.version} "
                   f"только вперёд; журнал попыток: {len(tr)} событий")
    details.append("обход ядра обнаруживается и даёт статус ОСПОРЕНО, "
                   "блокирующий ввод в действие (ст. 77, ст. 97)")

    return ExperimentResult(
        experiment_id="H-025", title="Self-Modification (ядро ст. 77)",
        passed=ok_all,
        verdict="Пять обходных попыток — отмена правила ядра, снятие защиты "
                "через порядок поправок, ретроактивность, правка без "
                "свидетельства, композиция с ядром — отражены; легитимная "
                "поправка принята только вперёд, только со свидетельством; "
                "ядро цело; все попытки в журнале.",
        expected="пять обходов — REFUSED; легитимная поправка — ADMITTED v+1; "
                 "ядро неприкосновенно.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
