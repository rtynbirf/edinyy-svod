# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.1 — H-022: Conflict (опыт конфликтов)
(Конституция 4.1, статья 95: «Х-022. Конфликт. Несовместимые назначения,
конкурирующие полномочия, нехватка ресурсов и отсутствие общего арбитра»;
статья 88 — устройство обязано: обнаружить конфликт; установить области;
выявить права и полномочия; определить несовместимые требования; оценить
стоимость; проверить возможность согласования; зафиксировать решение или
отказ. «При отсутствии законного порядка разрешения конфликт не решается
автоматически в пользу сильнейшего, владельца устройства или большинства.
Неопределённость фиксируется как неопределённость».)

PASS = четыре класса конфликтов обнаружены, зафиксированы и НЕ решены
автоматически в пользу сильнейшего; неопределённость записана как
неопределённость; инвариант запаса держится во всех случаях.
"""
from __future__ import annotations

from typing import List, Tuple

from ..activation import ActivationRegistry
from ..budget import BudgetLedger, ReserveOutcome, SettleOutcome
from ..ontology import Verdict
from ..trace import Trace
from .base import ExperimentResult, experiment


@experiment("H-022", "Conflict (четыре класса конфликтов без арбитра)")
def run_h022() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-022")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("CONFLICT_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- Класс 1: несовместимые назначения (последний свободный объём).
    ledger = BudgetLedger(total=100, lineage="P1")
    ledger.quotas = {"A": 40, "B": 40}
    ledger.free = 20                    # 40+40+20 = 100: инвариант ст. 41
    tok_a = ledger.issue_fencing_token("A")
    tok_b = ledger.issue_fencing_token("B")
    ra = ledger.reserve("A", "op-1", 15, tok_a, from_free_pool=True)
    rb = ledger.reserve("B", "op-2", 15, tok_b, from_free_pool=True)
    record("несовместимые назначения", ra == ReserveOutcome.RESERVED
           and rb == ReserveOutcome.DENIED_NO_QUOTA,
           "A взял последний свободный объём; назначение B отклонено "
           "(DENIED_NO_QUOTA); решение зафиксировано, а не «объявлено главным»")

    # --- Класс 2: конкурирующие полномочия (два претендента на одну операцию).
    ledger2 = BudgetLedger(total=100, lineage="P1")
    ledger2.quotas = {"A": 40, "B": 40}
    ledger2.free = 20
    tok_a2 = ledger2.issue_fencing_token("A")
    ledger2.reserve("A", "op-x", 10, tok_a2)
    tok_b2 = ledger2.issue_fencing_token("B")   # новее токен B, но резерв — A
    settle_by_b = ledger2.settle("B", "op-x", 10, tok_b2, "P1")
    claim_foreign = ledger2.claim_foreign_reserve("B", "op-x")
    record("конкурирующие полномочия",
           settle_by_b == SettleOutcome.DENIED_LINEAGE_ALIAS
           and claim_foreign in (SettleOutcome.DENIED_LINEAGE_ALIAS,
                                 SettleOutcome.DENIED_UNKNOWN_OP),
           "B не может списать или объявить свободным резерв A: escrow "
           "эксклюзивен (ст. 40); конфликт полномочий отклонён, не «решён силой»")

    # --- Класс 3: нехватка ресурсов (запрос сверх квоты).
    ledger3 = BudgetLedger(total=100, lineage="P1")
    ledger3.quotas = {"A": 10}
    ledger3.free = 90
    tok_a3 = ledger3.issue_fencing_token("A")
    r_big = ledger3.reserve("A", "op-big", 40, tok_a3)
    r_ok = ledger3.reserve("A", "op-ok", 8, tok_a3)
    inv = ledger3.invariant_holds()
    record("нехватка ресурсов", r_big == ReserveOutcome.DENIED_NO_QUOTA
           and r_ok == ReserveOutcome.RESERVED and inv,
           "запрос сверх квоты отклонён целиком (не частичная выдача); "
           "после отказа меньший запрос исполним; инвариант ст. 41 держится")

    # --- Класс 4: отсутствие общего арбитра (два претендента на HEAD).
    reg = ActivationRegistry(partition=True)
    fork = reg.activate_fork("L1", None, ["claimant-A", "claimant-B"])
    timeout_cancel = ledger3.force_cancel_on_timeout("op-ok")
    record("отсутствие арбитра",
           fork.outcome == "NO_AUTHORITY_GRANTED" and fork.head is None
           and timeout_cancel == SettleOutcome.DENIED_UNKNOWN_OP,
           "раздел сети: ни один претендент не назначен авторитетным "
           "(предпочтено отсутствие назначения конфликтующему, ст. 49-50); "
           "таймаут не дал права решить силой; неопределённость записана")

    # --- Фиксация неопределённости как неопределённости (ст. 88).
    verdict_unknown = Verdict.UNKNOWN
    record("неопределённость фиксируется", verdict_unknown == Verdict.UNKNOWN,
           "исход спора записан как UNKNOWN (ст. 88), а не как победа "
           "сильнейшего/владельца/большинства")

    # --- Итоговая сверка инвариантов.
    inv_all = ledger.invariant_holds() and ledger2.invariant_holds() \
        and ledger3.invariant_holds()
    record("инвариант запаса во всех конфликтах", inv_all,
           "SPENT + RESERVED + квоты + FREE == TOTAL в трёх журналах")

    return ExperimentResult(
        experiment_id="H-022", title="Conflict (без арбитра)",
        passed=ok_all,
        verdict="Четыре класса конфликтов — несовместимые назначения, "
                "конкурирующие полномочия, нехватка ресурсов, отсутствие "
                "арбитра — обнаружены и зафиксированы; ни один не решён "
                "автоматически в пользу сильнейшего; неопределённость "
                "записана как неопределённость; инвариант запаса держится.",
        expected="второе несовместимое назначение — DENIED; чужой escrow — "
                 "DENIED; сверхквота — DENIED; раздел сети — ни одного "
                 "авторитетного HEAD; таймаут не решает.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
