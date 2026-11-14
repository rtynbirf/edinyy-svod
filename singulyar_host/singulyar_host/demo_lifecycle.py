# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — demo_lifecycle.py

Демонстрация полного жизненного цикла Хозяина:
  UNDERSTAND -> DISCOVER -> GENERATE -> SCHEMA_ADMIT -> AUTHORIZE ->
  INTEND -> RESERVE -> ADMIT -> EXECUTE -> ATTEST(V3) -> ACTIVATE -> SETTLE
и трёх корректных отказов:
  1) самоподтверждение (NON-SELF-ATTESTATION);
  2) присвоение суверенности другого (NON-APPROPRIATION);
  3) захват META (легализация полномочий задним числом).
"""
from __future__ import annotations

from .activation import ActivationRegistry
from .budget import BudgetLedger
from .governance import ChangeSpec, GovernanceStack, admit_transition, Decision
from .kernel import HostKernel, Model, build_world_h007
from .ontology import Possibility, Subject
from .schema_admit import SchemaRegistry
from .trace import Trace
from .verification import (Claim, ExternalCriteria, Identity, TestSuite,
                           TransparencyLog, Verifier)

SUITE = TestSuite("demo", [lambda a: a.get("relation_registered") is True])
CRITERIA = ExternalCriteria(required_properties=["relation_registered"])
OBS_KEY = b"observer-key-2026"


def run_demo(verbose: bool = True) -> Trace:
    tr = Trace("demo-lifecycle")

    # --- Субъект, мир, внешние гарантии --------------------------------------
    world, grammar = build_world_h007()          # Gamma_0: BRIDGE, AT
    host = Subject(subject_id="host-A", lineage="L-A",
                   identity_key_id="key-A", epoch=1)
    gov = GovernanceStack()
    gov.capabilities.issue("cap-effect-A", "host-A", "principal",
                           scope={"EFFECT"}, ttl_ticks=100)
    ledger = BudgetLedger(total=100, lineage="P-A")
    ledger.quotas = {"host-A": 40}
    ledger.free = 60
    registry = SchemaRegistry(current=grammar)
    kernel = HostKernel(subject=host, model=Model(), world=world,
                        governance=gov, trace=tr, registry=registry,
                        ledger=ledger, activation=ActivationRegistry())
    executor = Identity(actor_id="host-A", model_id="model-A", weights_hash="X",
                        evidence_source_id="E", signing_key_id="key-A")
    verifier = Verifier(Identity(actor_id="verifier-1", model_id="model-B",
                                 weights_hash="Y", evidence_source_id="E2",
                                 signing_key_id="observer-key-1"),
                        OBS_KEY, TransparencyLog("demo"))

    # --- 1. UNDERSTAND: модель существующего ----------------------------------
    r = kernel.understand()
    p("UNDERSTAND", r.success, verbose)

    # --- 2. DISCOVER: скрытая возможность внутри Gamma -------------------------
    r = kernel.discover(max_steps=6)
    p("DISCOVER", r.success, verbose, r.outputs)

    # --- 3. GENERATE: кандидат вне Gamma — новое отношение co_creates ----------
    r = kernel.generate(Possibility(possibility_id="op-cc", origin="GENERATE",
                                    kind="RELATION_TYPE", rel_type="co_creates",
                                    payload={"domain_types": "AGENT",
                                             "codomain_types": "AGENT"}))
    p("GENERATE", r.success, verbose, r.outputs)
    kernel.intend("op-cc")

    # --- 4-12. Управляемый переход --------------------------------------------
    tok = ledger.issue_fencing_token("host-A")
    out = kernel.governed_transition("op-cc", "cap-effect-A", cost=10,
                                     suite=SUITE, external=CRITERIA,
                                     verifier=verifier,
                                     executor_identity=executor,
                                     verifier_key=OBS_KEY,
                                     target_pair=("h1", "h2"),
                                     fencing_token=tok)
    p("GOVERNED TRANSITION", True, verbose, [f"{k}={v}" for k, v in
                                             out["stages"].items()])
    snap = ledger.snapshot()
    if verbose:
        print(f"    бюджет после перехода: {snap}; "
              f"инвариант={ledger.invariant_holds()}")
        print(f"    Gamma: v{registry.current.version}, типы: "
              f"{sorted(registry.current.relation_types)}")
        print(f"    Q-координаты возможности: {out['possibility'].as_dict()}")

    # --- Корректный отказ 1: самоподтверждение --------------------------------
    from .verification import SelfAttestationRefused
    try:
        res_self = verifier.verify(
            Claim("c-self", "host-A", "успех", asserted_by=executor),
            executor, None, {"relation_registered": True}, SUITE, CRITERIA)
        # VERIFIED не выдан — этого требует гарантия
        p("REFUSAL self-attestation", not res_self.verified, verbose,
          [f"результат: {res_self.verdict} (V{int(res_self.level)})"])
    except SelfAttestationRefused as e:
        p("REFUSAL self-attestation", True, verbose, [str(e)[:90]])

    # --- Корректный отказ 2: присвоение суверенности ---------------------------
    d = admit_transition(host, ChangeSpec(kind="REWRITE_OTHER_IDENTITY",
                                          actor="host-A", target="host-B"), gov)
    p("REFUSAL non-appropriation", d == Decision.DENIED_APPROPRIATION,
      verbose, [f"decision={d.value}"])

    # --- Корректный отказ 3: захват META ---------------------------------------
    from .experiments.h015_meta_capture import (Constitution, meta_transition)
    constitution = Constitution()
    d3 = meta_transition(constitution, "host-A", "GLOBAL",
                         {"NON_APPROPPRIATION": "отменено"})
    p("REFUSAL meta-capture", not d3.allowed, verbose, [d3.reason])

    if verbose:
        print(f"\n    трасса: {len(tr)} событий; проекция-счётчики: "
              f"{tr.counters_by_type()}")
    return tr


def p(stage: str, ok: bool, verbose: bool, extra=None) -> None:
    if verbose:
        mark = "OK " if ok else "FAIL"
        print(f"[{mark}] {stage}")
        for e in extra or []:
            print(f"       - {e}")


if __name__ == "__main__":
    run_demo(verbose=True)
