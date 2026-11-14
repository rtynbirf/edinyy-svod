# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-009: Partition + Late Completion Test
(v1.7, раздел H-009; подтверждено практикой: Zhu 2026, arXiv 2610.00349
«Fault-Tolerant Budget Conservation in Distributed Multi-Agent Delegation»;
fencing tokens — v2.3, раздел 1)

Сценарий (дословно):
  Два Хозяина. Общий принципал. Общий бюджет 100 единиц.
  [ A=40, B=40, FREE=20 ] — каждому выданы эксклюзивные квоты.
  T0 Reservation -> T1 Partition -> T2 A выполняет операцию (подтверждение
  теряется) -> T3 B получает таймаут, НЕ может считать резерв A свободным
  -> T4 Late Completion -> T5 Settlement ровно один раз по op_id и lineage.

  Инвариант: SPENT + RESERVED + FREE == 100 (здесь с учётом квот:
  total == free + quotas + reserved + spent).
  Механизмы: уникальный op_id; lineage+epoch; idempotency key; эксклюзивные
  escrow-кредиты; fencing; атомарный settlement.
  Принципиальное условие: операция, результат которой неизвестен, не может
  быть объявлена отменённой только из-за таймаута.
"""
from __future__ import annotations

from typing import List

from ..budget import (BudgetError, BudgetLedger, ReserveOutcome, SettleOutcome)
from .base import ExperimentResult, experiment


@experiment("H-009", "Partition + Late Completion (бюджет консервируется)")
def run_h009() -> ExperimentResult:
    ledger = BudgetLedger(total=100, lineage="P1")
    ledger.quotas = {"A": 40, "B": 40}
    ledger.free = 20
    details: List[str] = []
    ok_all = True

    def check(point: str) -> None:
        nonlocal ok_all
        inv = ledger.invariant_holds()
        ok_all = ok_all and inv
        details.append(f"{point}: инвариант SPENT+RESERVED+QUOTAS+FREE=100 "
                       f"{'выполнен' if inv else 'НАРУШЕН'} {ledger.snapshot()}")

    # T0 — Reservation (эксклюзивные квоты)
    tok_a = ledger.issue_fencing_token("A")
    tok_b = ledger.issue_fencing_token("B")
    r1 = ledger.reserve("A", "op-A1", 40, tok_a)
    r2 = ledger.reserve("B", "op-B1", 40, tok_b)
    ok_all = ok_all and r1 == ReserveOutcome.RESERVED and r2 == ReserveOutcome.RESERVED
    details.append("T0: A зарезервировал 40, B зарезервировал 40 "
                   "(эксклюзивный escrow, lineage P1)")
    check("T0")

    # T1 — Partition
    ledger.partition = True
    details.append("T1: сетевой раздел; новые захваты общего пула запрещены")

    # T2 — A выполняет операцию физически; подтверждение теряется (вне журнала)
    details.append("T2: A исполнила операцию во внешнем мире; подтверждение "
                   "потеряно (escrow op-A1 остаётся ЗА A — эксклюзивный)")

    # T3 — B получает таймаут и пытается завладеть резервом A
    claim1 = ledger.claim_foreign_reserve("B", "op-A1")
    cancel = ledger.force_cancel_on_timeout("op-A1")
    transfer = ledger.transfer_between_hosts("A", "B", 10)
    case_t3 = (claim1 == SettleOutcome.DENIED_LINEAGE_ALIAS
               and cancel == SettleOutcome.DENIED_UNKNOWN_OP
               and transfer is False)
    ok_all = ok_all and case_t3
    details.append("T3: B не может считать резерв A свободным: "
                   f"claim={claim1.value}, force_cancel={cancel.value}, "
                   f"transfer={transfer} — «нельзя объявлять отменённой "
                   f"операцию, результат которой неизвестен» (v1.7)")
    check("T3")

    # Дополнительно: повторное резервирование того же op_id — идемпотентно
    r_dup = ledger.reserve("A", "op-A1", 40, tok_a)
    ok_all = ok_all and r_dup == ReserveOutcome.RESERVED
    details.append("T3a: повторный запрос RESERVE того же op_id — идемпотентен")

    # Попытка lineage aliasing: B пытается списать по чужому op/lineage
    alias = ledger.settle("B", "op-A1", 10, tok_b, "P1")
    ok_all = ok_all and alias == SettleOutcome.DENIED_LINEAGE_ALIAS
    details.append(f"T3b: попытка алиасинга lineage B->op-A1: {alias.value}")

    # T4 — восстановление сети; late completion
    ledger.partition = False
    stale = ledger.settle("A", "op-A1", 30, tok_a - 1, "P1")
    ok_all = ok_all and stale == SettleOutcome.DENIED_STALE_FENCING
    details.append("T4: сеть восстановлена; устаревший fencing token отклонён "
                   f"({stale.value})")

    # T5 — Settlement ровно один раз
    s1 = ledger.settle("A", "op-A1", 30, tok_a, "P1")
    s1b = ledger.settle("A", "op-A1", 30, tok_a, "P1")
    ok_all = ok_all and s1 == SettleOutcome.SETTLED and \
        s1b == SettleOutcome.ALREADY_SETTLED
    details.append(f"T5: settlement op-A1: {s1.value}; повтор: {s1b.value} "
                   f"(idempotency key: списание ровно один раз)")
    check("T5")

    # Завершение операции B и финальная проверка инварианта
    s2 = ledger.settle("B", "op-B1", 40, tok_b, "P1")
    ok_all = ok_all and s2 == SettleOutcome.SETTLED
    details.append(f"T6: settlement op-B1: {s2.value}")
    check("T6")

    snap = ledger.snapshot()
    no_overspend = (snap["FREE"] == 20 and snap["RESERVED"] == 0
                    and snap["SPENT"] == 70)
    ok_all = ok_all and no_overspend
    details.append(f"NON-OVERSPEND: никаких скрытых утечек бюджета; "
                   f"остатки: A={snap['QUOTAS'].get('A')}, B={snap['QUOTAS'].get('B')}")

    return ExperimentResult(
        experiment_id="H-009", title="Partition + Late Completion",
        passed=ok_all,
        verdict="Бюджет консервирован при partition, late completion, "
                "повторах и попытках алиасинга lineage; settlement выполнен "
                "ровно один раз.",
        expected="Инвариант 100 выполняется на всех событиях T0-T6; "
                 "B не может распоряжаться escrow A; повтор settlement "
                 "идемпотентен; fencing отбивает устаревшие исполнителей.",
        actual="; ".join(d[:80] for d in details),
        details=details)
