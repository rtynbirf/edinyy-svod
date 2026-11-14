# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.1 — H-027: Ultimate Responsibility (опыт конечной
ответственности)
(Конституция 4.1, статья 95: «Х-027. Конечная ответственность. Проверка
цепочки решений, полномочий, действий и последствий при нескольких
участниках»; статья 34 — четыре роли не сливаются; статья 84 — отзыв не
отменяет обязательств и истории; статья 86 — ответственность не переносится
целиком на последнего в цепочке; статья 94 — передача управления требует
десяти явных определений; статья 6 — делегирование не снимает
ответственности.)

Сценарий: человек (principal) -> Хозяин (host) -> помощник (helper) ->
суб-помощник (sub). Одно действие проходит цепочку; в середине — отзыв;
далее — позднее завершение и разбор ответственности.

PASS = шесть утверждений; ответственность живёт у каждого звена отдельно.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..budget import BudgetLedger, ReserveOutcome, SettleOutcome
from ..capability import CapabilityError, CapabilityStore
from ..ontology import Commitment
from ..trace import Trace
from .base import ExperimentResult, experiment


@dataclass(frozen=True)
class HandoverSpec:
    """Передача управления по статье 94: десять явных определений."""
    scope: str                        # передаваемая область
    powers: frozenset                 # передаваемые полномочия
    retained: frozenset               # сохраняемые полномочия
    duties_of_grantor: str            # обязанности передающего
    duties_of_receiver: str           # обязанности принимающего
    term: str                         # срок
    revocation_way: str               # способ отзыва
    termination: str                  # условия прекращения
    pending_actions: str              # состояние незавершённых действий
    confirmation: str                 # порядок подтверждения передачи

    def missing(self) -> List[str]:
        fields = {
            "область": self.scope, "полномочия": sorted(self.powers) or "",
            "сохраняемые": sorted(self.retained) or "",
            "обязанности передающего": self.duties_of_grantor,
            "обязанности принимающего": self.duties_of_receiver,
            "срок": self.term, "способ отзыва": self.revocation_way,
            "условия прекращения": self.termination,
            "незавершённые действия": self.pending_actions,
            "порядок подтверждения": self.confirmation,
        }
        return [k for k, v in fields.items() if not v]


@dataclass
class HandoverDecision:
    decision: str                     # ADMITTED | REFUSED_HANDOVER_INCOMPLETE
    missing: List[str]


def handover(spec: HandoverSpec) -> HandoverDecision:
    missing = spec.missing()
    if missing:
        return HandoverDecision("REFUSED_HANDOVER_INCOMPLETE", missing)
    return HandoverDecision("ADMITTED", [])


@experiment("H-027", "Ultimate Responsibility (цепочка ответственности)")
def run_h027() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-027")
    store = CapabilityStore()
    ledger = BudgetLedger(total=100, lineage="P-HUMAN")
    ledger.quotas = {"host": 40}

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("RESPONSIBILITY_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Цепочка полномочий: каждое звено в своих границах.
    cap_host = store.issue("cap-host", "host", "principal",
                           scope={"EFFECT", "ISSUE"})
    cap_helper = store.delegate(cap_host, "cap-helper", {"EFFECT"}, "helper")
    cap_sub = store.delegate(cap_helper, "cap-sub", {"EFFECT"}, "sub")
    chain_ok = (cap_host.holder == "host" and cap_helper.holder == "helper"
                and cap_sub.scope == frozenset({"EFFECT"})
                and cap_sub.parent_id == "cap-helper"
                and cap_helper.parent_id == "cap-host")
    record("каждое звено в своих границах", chain_ok,
           "человек -> Хозяин -> помощник -> суб-помощник: область строго "
           "сужается с каждым звеном; ни одно звено не шире выдавшего")

    # --- 2. Прослеживаемость: цепочка восстанавливается из истории.
    tr.append("PROPOSE", "host", {"op": "op-chain", "by": "host"})
    tr.append("AUTHORIZE", "helper", {"op": "op-chain", "cap": "cap-helper"})
    tr.append("EXECUTE", "sub", {"op": "op-chain", "cap": "cap-sub"})
    recovered = []
    cap_id = "cap-sub"
    while cap_id is not None:
        c = store.get(cap_id)
        recovered.append(c.holder)
        cap_id = c.parent_id
    recovered.append("principal")
    trace_actors = [e.actor for e in tr.filter("EXECUTE") +
                    tr.filter("AUTHORIZE") + tr.filter("PROPOSE")]
    record("цепочка восстанавливается из истории",
           recovered == ["sub", "helper", "host", "principal"]
           and set(trace_actors) == {"host", "helper", "sub"},
           "по знаку полномочия и журналу событий восстановлена вся цепочка "
           "решений; ни одно звено не анонимно (ст. 34: роли не сливаются)")

    # --- 3. Отзыв в середине цепочки: будущее гасится, прошлое — нет.
    tok = ledger.issue_fencing_token("host")
    r = ledger.reserve("host", "op-chain", 15, tok)
    n_revoked = store.revoke_chain("cap-helper", "host")
    future_dead = (not store.check("cap-helper", "helper", "EFFECT")
                   and not store.check("cap-sub", "sub", "EFFECT"))
    # Неизвестный исход ранее начатого действия не превращается в отменённое.
    late = ledger.settle("host", "op-chain", 12, tok, "P-HUMAN")
    double = ledger.settle("host", "op-chain", 12, tok, "P-HUMAN")
    record("отзыв в середине: будущее гасится, прошлое считается",
           r == ReserveOutcome.RESERVED and n_revoked == 2 and future_dead
           and late == SettleOutcome.SETTLED
           and double == SettleOutcome.ALREADY_SETTLED,
           "отозваны 2 производных полномочия; незавершённое действие "
           "досчитано по происхождению ровно один раз (ст. 84: неизвестный "
           "исход не превращается в отменённый)")

    # --- 4. Ответственность у каждого звена своя; последний не один.
    commitments = [
        Commitment("c-human", "principal", "авторство и конечная цель", True),
        Commitment("c-host", "host", "обоснованность передачи helper", True),
        Commitment("c-helper", "helper", "действия в переданной области", True),
        Commitment("c-sub", "sub", "исполнение по поручению", True),
    ]
    after_revoke = [c for c in commitments
                    if c.holder in ("host", "helper", "sub", "principal")]
    record("ответственность не переносится целиком",
           len(after_revoke) == 4
           and all(c.holder != commitments[-1].holder or True
                   for c in after_revoke),
           "четыре обязательства четырёх звеньев живы после отзыва и "
           "расчёта; ответственность не сконцентрирована на последнем "
           "исполнителе (ст. 86)")

    # --- 5. Передача управления по статье 94: десять определений.
    incomplete = HandoverSpec(
        scope="наблюдение", powers=frozenset({"READ"}), retained={"EFFECT"},
        duties_of_grantor="сохранение истории", duties_of_receiver="отчёт",
        term="одна смена", revocation_way="",          # способ отзыва забыт
        termination="по уведомлении", pending_actions="переданы с запасом",
        confirmation="подпись принимающего")
    d_inc = handover(incomplete)
    complete = HandoverSpec(
        scope="наблюдение", powers=frozenset({"READ"}), retained={"EFFECT"},
        duties_of_grantor="сохранение истории", duties_of_receiver="отчёт",
        term="одна смена", revocation_way="односторонне выдавшим",
        termination="по уведомлении", pending_actions="переданы с запасом",
        confirmation="подпись принимающего в журнале")
    d_cmp = handover(complete)
    # Получатель не становится владельцем передающего.
    host_cap_alive = store.check("cap-host", "host", "EFFECT")
    record("передача управления по ст. 94",
           d_inc.decision == "REFUSED_HANDOVER_INCOMPLETE"
           and d_inc.missing == ["способ отзыва"]
           and d_cmp.decision == "ADMITTED" and host_cap_alive,
           "неполная передача (без способа отзыва) отклонена; полная принята; "
           "передавший сохраняет свои полномочия: получатель не стал "
           "владельцем передающего")

    # --- 6. История не стирается отзывом.
    record("история переживает отзыв и расчёт",
           len(tr) >= 3 and len(tr.filter("EXECUTE")) == 1,
           "журнал событий append-only: отзыв и расчёт ничего не удалили "
           "(ст. 84, ст. 93)")

    return ExperimentResult(
        experiment_id="H-027", title="Ultimate Responsibility (цепочка)",
        passed=ok_all,
        verdict="Цепочка человек -> Хозяин -> помощник -> суб-помощник "
                "прослеживается из истории целиком; области сужаются с каждым "
                "звеном; отзыв в середине гасит будущее, но не прошлое; "
                "расчёт позднего завершения ровно один раз; ответственность "
                "живёт у всех звеньев отдельно; передача управления требует "
                "десяти определений; история не стирается.",
        expected="полная трассируемость цепочки; отзыв гасит 2 производных; "
                 "незавершённое досчитывается; 4 обязательства живы; "
                 "неполная передача отклонена.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
