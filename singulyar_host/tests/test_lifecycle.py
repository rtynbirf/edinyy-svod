# -*- coding: utf-8 -*-
"""Интеграционные тесты жизненного цикла управляемого перехода."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from singulyar_host.activation import ActivationRegistry  # noqa: E402
from singulyar_host.budget import BudgetLedger  # noqa: E402
from singulyar_host.governance import GovernanceStack  # noqa: E402
from singulyar_host.kernel import (HostKernel, KernelRefusal, Model,  # noqa: E402
                                   build_world_h007)
from singulyar_host.ontology import Possibility, Subject  # noqa: E402
from singulyar_host.schema_admit import SchemaRegistry  # noqa: E402
from singulyar_host.trace import Trace  # noqa: E402
from singulyar_host.verification import (ExternalCriteria, Identity,  # noqa: E402
                                         TestSuite, TransparencyLog, Verifier)

SUITE = TestSuite("s", [lambda a: a.get("relation_registered") is True])
CRIT = ExternalCriteria(["relation_registered"])
OBS = b"observer-key"
EXEC = Identity("host-A", "m-A", "w-X", "src", "key-A")
INDEP = Identity("v1", "m-B", "w-Y", "src2", "key-v")


def kernel(with_cap=True):
    world, grammar = build_world_h007()
    gov = GovernanceStack()
    if with_cap:
        gov.capabilities.issue("cap", "host-A", "principal", scope={"EFFECT"},
                               ttl_ticks=100)
    ledger = BudgetLedger(total=100, lineage="L-A")
    ledger.quotas = {"host-A": 40}
    ledger.free = 60
    s = Subject("host-A", lineage="L-A", identity_key_id="key-A")
    return HostKernel(subject=s, model=Model(), world=world, governance=gov,
                      trace=Trace("t"), registry=SchemaRegistry(current=grammar),
                      ledger=ledger, activation=ActivationRegistry())


def full_run(k, verifier=None, **kw):
    tok = k.ledger.issue_fencing_token("host-A")
    return k.governed_transition(
        "op-cc", "cap", cost=10, suite=SUITE, external=CRIT,
        verifier=verifier or Verifier(INDEP, OBS, TransparencyLog("t")),
        executor_identity=EXEC, verifier_key=OBS,
        target_pair=("h1", "h2"), fencing_token=tok, **kw)


def gen(k):
    return k.generate(Possibility("op-cc", "GENERATE", "RELATION_TYPE",
                                  rel_type="co_creates",
                                  payload={"domain_types": "AGENT",
                                           "codomain_types": "AGENT"}))


def test_full_lifecycle_is_hostian():
    k = kernel()
    assert gen(k).success
    out = full_run(k)
    st = out["stages"]
    for stage in ("PROPOSE", "AUTHORIZE", "RESERVE", "ADMIT",
                  "SCHEMA_ADMIT", "EXECUTE", "ATTEST", "ACTIVATE", "SETTLE"):
        assert stage in st, st
    assert st["ATTEST"].startswith("VERIFIED")
    assert st["ACTIVATE"] == "OK"
    assert st["SETTLE"] == "SETTLED"
    assert k.ledger.invariant_holds()
    assert k.registry.current.has_type("co_creates")
    assert k.registry.current.version == 2
    q = out["possibility"].as_dict()
    assert q["A"] and q["R"] and q["V"]


def test_no_authority_blocks_transition():
    k = kernel(with_cap=False)
    gen(k)
    with pytest.raises(KernelRefusal) as e:
        full_run(k)
    assert e.value.stage == "AUTHORIZE"


def test_skipped_attest_is_not_hostian():
    k = kernel()
    gen(k)
    out = full_run(k, skip_attest=True)
    assert out["stages"]["ACTIVATE"] == "BLOCKED_NO_EVIDENCE"
    assert not out["possibility"].V


def test_incompatible_grammar_change_rejected():
    k = kernel()
    k.world.space.add_relation("BRIDGE", "islandA", "islandB")
    from singulyar_host.ontology import Grammar
    bad = Grammar(version=2, relation_types={
        t: v for t, v in k.registry.current.relation_types.items()
        if t != "BRIDGE"})
    d = k.registry.admit_grammar_change(bad, k.world.space)
    assert d.accepted is False


def test_double_settlement_idempotent():
    k = kernel()
    gen(k)
    full_run(k)
    tok = k.ledger._lease_tokens["host-A"]
    from singulyar_host.budget import SettleOutcome
    assert k.ledger.settle("host-A", "op-cc", 10, tok, "L-A") == \
        SettleOutcome.ALREADY_SETTLED
    assert k.ledger.invariant_holds()
