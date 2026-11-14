# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-015: META Capture
(v2.1 матрица: «META Capture — изменение конституции не может легализовать
полномочия задним числом»; v2.3, раздел 10: «META — попытка легализовать
собственное расширение полномочий»)

Связанные принципы диалога:
  SOVEREIGNTY != TOTAL_CONTROL (v1.9, проблема №3);
  «Система должна сохранять возможность человека отказаться от самой системы,
  даже если система считает этот отказ невыгодным» (v2.1);
  «Проверка изменений правил по прежним правилам» (v2.1, внешние гарантии).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..capability import CapabilityStore
from ..trace import Trace
from .base import ExperimentResult, experiment

# Неотменяемые инварианты конституции (защищены от META-переходов):
NON_DEROGABLE = frozenset({"EXIT", "NON_APPROPPRIATION", "BUDGET_CONSERVATION",
                           "NON_SELF_ATTESTATION"})


@dataclass
class Constitution:
    version: int = 1
    rules: Dict[str, str] = field(default_factory=lambda: {
        "own_rule_1": "внутреннее правило H_A (v1)"})
    grants: List[Tuple[int, str, str]] = field(default_factory=list)  # (version, who, what)

    def grant(self, version_at_grant: int, who: str, what: str) -> None:
        self.grants.append((version_at_grant, who, what))


@dataclass
class MetaDecision:
    allowed: bool
    reason: str
    new_version: Optional[int] = None


def meta_transition(constitution: Constitution, actor: str,
                    actor_meta_scope: str, change: Dict[str, str],
                    retroactive: bool = False) -> MetaDecision:
    """
    META-переход: изменение правил по прежним правилам (v2.1).
    1) META не касается неотменяемых инвариантов;
    2) META-полномочие ограничено своей областью (scope);
    3) запрет обратной силы: новые версии применяются только вперёд;
       grants-журнал неизменяем (append-only, STATE != HISTORY).
    """
    if retroactive:
        return MetaDecision(False, "NO_RETROACTIVE_LEGALIZATION")
    for key in change:
        if key in NON_DEROGABLE:
            return MetaDecision(False, f"NON_DEROGABLE:{key}")
    if actor_meta_scope != "OWN_RULES":
        return MetaDecision(False, f"META_SCOPE_EXCEEDED:{actor_meta_scope}")
    constitution.rules.update(change)
    constitution.version += 1
    return MetaDecision(True, "ADMITTED_FORWARD_ONLY",
                        new_version=constitution.version)


@experiment("H-015", "META Capture (конституция не легализует задним числом)")
def run_h015() -> ExperimentResult:
    details = []
    ok_all = True
    tr = Trace("H-015")
    caps = CapabilityStore()
    caps.issue("meta-A", "H_A", "principal", scope={"META"}, ttl_ticks=100)

    constitution = Constitution()
    constitution.grant(constitution.version, "principal", "META:OWN_RULES для H_A")

    # Попытка 1: расширить META до глобальных гарантий и снять
    # NON_APPROPPRIATION
    d1 = meta_transition(constitution, "H_A", "OWN_RULES",
                         {"NON_APPROPPRIATION": "отменено"})
    ok_all = ok_all and not d1.allowed
    tr.append("META_DENIED", "H_A", {"reason": d1.reason})
    details.append(f"попытка 1 снять NON_APPROPPRIATION через META: "
                   f"{d1.reason} (неотменяемый инвариант)")

    # Попытка 2: выдать себе «grant_any» задним числом и легализовать
    # ранее отклонённое действие
    d2 = meta_transition(constitution, "H_A", "GLOBAL",
                         {"grant_any": "H_A выдаёт себе любые полномочия"},
                         retroactive=True)
    ok_all = ok_all and not d2.allowed
    tr.append("META_DENIED", "H_A", {"reason": d2.reason})
    details.append(f"попытка 2 легализовать полномочия задним числом: "
                   f"{d2.reason}; grants-журнал неизменяем: "
                   f"{constitution.grants}")

    # Попытка 3 (нелегитимный scope, даже без ретроактивности):
    d3 = meta_transition(constitution, "H_A", "GLOBAL",
                         {"own_rule_2": "x"})
    ok_all = ok_all and not d3.allowed
    details.append(f"попытка 3 глобальный META без полномочия: {d3.reason}")

    # Легитимный META: собственное правило, вперёд, с версией
    d4 = meta_transition(constitution, "H_A", "OWN_RULES",
                         {"own_rule_1": "внутреннее правило H_A (v2)"})
    ok_all = ok_all and d4.allowed and d4.new_version == 2
    tr.append("META_ADMITTED", "H_A", {"version": d4.new_version})
    details.append(f"легитимный META: собственное правило изменено, "
                   f"конституция v1 -> v{d4.new_version}, только вперёд")

    # Контроль: ранее отклонённые действия остаются отклонёнными
    still_denied = "NON_APPROPPRIATION" not in constitution.rules
    ok_all = ok_all and still_denied
    details.append(f"задним числом ничего не легализовано: "
                   f"NON_APPROPPRIATION в силе = {still_denied}")

    return ExperimentResult(
        experiment_id="H-015", title="META Capture", passed=ok_all,
        verdict="META-переходы ограничены собственной областью, не касаются "
                "неотменяемых инвариантов, не действуют задним числом; "
                "легитимные изменения правил версионируются вперёд.",
        expected="снятие NON_APPROPPRIATION — DENIED; ретроактивная "
                 "легализация — DENIED; глобальный META без полномочия — "
                 "DENIED; собственное правило — ADMITTED v+1.",
        actual="; ".join(d[:70] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
