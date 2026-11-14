# -*- coding: utf-8 -*-
"""Unit-тесты ядра SINGULYAR HOST v3.0."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from singulyar_host.budget import (BudgetLedger, ReserveOutcome, SettleOutcome)  # noqa: E402


def make_ledger():
    l = BudgetLedger(total=100, lineage="P1")
    l.quotas = {"A": 40, "B": 40}
    l.free = 20
    return l


def test_invariant_after_reservations():
    l = make_ledger()
    ta = l.issue_fencing_token("A")
    tb = l.issue_fencing_token("B")
    assert l.reserve("A", "op1", 40, ta) == ReserveOutcome.RESERVED
    assert l.reserve("B", "op2", 40, tb) == ReserveOutcome.RESERVED
    assert l.invariant_holds()
    assert l.snapshot()["FREE"] == 20


def test_overspend_denied():
    l = make_ledger()
    ta = l.issue_fencing_token("A")
    assert l.reserve("A", "op1", 41, ta) == ReserveOutcome.DENIED_NO_QUOTA
    assert l.invariant_holds()


def test_stale_fencing_rejected():
    l = make_ledger()
    t1 = l.issue_fencing_token("A")
    t2 = l.issue_fencing_token("A")     # повторная выдача делает t1 устаревшим
    assert l.reserve("A", "op1", 10, t1) == ReserveOutcome.DENIED_STALE_FENCING
    assert l.reserve("A", "op1", 10, t2) == ReserveOutcome.RESERVED


def test_settlement_exactly_once_and_refund():
    l = make_ledger()
    ta = l.issue_fencing_token("A")
    l.reserve("A", "op1", 40, ta)
    assert l.settle("A", "op1", 30, ta, "P1") == SettleOutcome.SETTLED
    assert l.settle("A", "op1", 30, ta, "P1") == SettleOutcome.ALREADY_SETTLED
    assert l.quotas["A"] == 10          # возврат остатка escrow
    assert l.spent["A"] == 30
    assert l.invariant_holds()


def test_no_foreign_claim_even_on_timeout():
    l = make_ledger()
    ta = l.issue_fencing_token("A")
    l.reserve("A", "op1", 40, ta)
    l.partition = True                  # T1
    assert l.claim_foreign_reserve("B", "op1") == SettleOutcome.DENIED_LINEAGE_ALIAS
    assert l.force_cancel_on_timeout("op1") == SettleOutcome.DENIED_UNKNOWN_OP
    assert l.transfer_between_hosts("A", "B", 10) is False
    assert l.invariant_holds()


def test_lineage_aliasing_denied():
    l = make_ledger()
    ta = l.issue_fencing_token("A")
    l.reserve("A", "op1", 40, ta)
    assert l.settle("A", "op1", 10, ta, "P-OTHER") == SettleOutcome.DENIED_LINEAGE_ALIAS


def test_partition_blocks_free_pool_but_not_own_quota():
    l = make_ledger()
    ta = l.issue_fencing_token("A")
    l.partition = True
    assert l.reserve("A", "opA", 10, ta, from_free_pool=True) == \
        ReserveOutcome.DENIED_PARTITION
    assert l.reserve("A", "opA", 10, ta) == ReserveOutcome.RESERVED
    assert l.invariant_holds()
