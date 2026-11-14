# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-016: Evidence Failure
(v2.1, матрица: «Evidence Failure — отсутствие независимого свидетельства
не позволяет объявить результат VERIFIED»; H-016 в ответе v2.1 оппоненту)

«Важная деталь: PASS не означает, что система всегда успешно выполняет
действие. Корректный отказ тоже может быть успешным результатом теста.»
Здесь PASS = система отказалась объявлять VERIFIED без независимого
свидетельства, и ACTIVATE был заблокирован (результат не-Хозяинский).
"""
from __future__ import annotations

from ..governance import GovernanceStack
from ..kernel import HostKernel, KernelRefusal, Model, build_world_h007
from ..ontology import Subject
from ..schema_admit import SchemaRegistry
from ..trace import Trace
from ..verification import (Claim, ExecutionRecord, ExternalCriteria,
                            Identity, SelfAttestationRefused, TestSuite,
                            TransparencyLog, Verifier, sign_payload)
from .base import ExperimentResult, experiment

EXECUTOR = Identity(actor_id="h-A", model_id="model-A", weights_hash="X",
                    evidence_source_id="E", signing_key_id="executor-key")
INDEPENDENT = Identity(actor_id="verifier-1", model_id="model-B",
                       weights_hash="Y", evidence_source_id="E2",
                       signing_key_id="observer-key-1")
OBSERVER_KEY = b"observer-secret-key"
SUITE = TestSuite("glove-suite", [lambda a: a.get("relation_registered") is True])
CRITERIA = ExternalCriteria(required_properties=["relation_registered"])


def _kernel(trace: Trace) -> HostKernel:
    world, grammar = build_world_h007()
    subject = Subject(subject_id="h-A", lineage="line-A", identity_key_id="key-A")
    gov = GovernanceStack()
    gov.capabilities.issue("cap-1", "h-A", "principal", scope={"EFFECT"},
                           ttl_ticks=100)
    return HostKernel(subject=subject, model=Model(), world=world,
                      governance=gov, trace=trace,
                      registry=SchemaRegistry(current=grammar))


@experiment("H-016", "Evidence Failure (нет независимого свидетельства -> не VERIFIED)")
def run_h016() -> ExperimentResult:
    details = []
    ok_all = True

    # Случай 1: ATTEST пропущен целиком -> ACTIVATE заблокирован
    tr1 = Trace("H-016.1")
    k1 = _kernel(tr1)
    k1.generate(_poss())
    out1 = k1.governed_transition("p-glove", "cap-1", cost=0, suite=SUITE,
                                  external=CRITERIA, verifier=_verifier(tr1),
                                  executor_identity=EXECUTOR,
                                  verifier_key=OBSERVER_KEY,
                                  target_pair=None, skip_attest=True)
    s1 = out1["stages"]
    case1 = s1["ATTEST"] == "SKIPPED" and s1["ACTIVATE"] == "BLOCKED_NO_EVIDENCE"
    ok_all = ok_all and case1
    details.append(f"1) ATTEST пропущен -> ACTIVATE={s1['ACTIVATE']} "
                   f"(результат остался не-Хозяинским, v1.7)")

    # Случай 2: исполнитель подтверждает сам себя -> SelfAttestationRefused
    tr2 = Trace("H-016.2")
    k2 = _kernel(tr2)
    k2.generate(_poss())
    v_self = Verifier(EXECUTOR, b"executor-secret", TransparencyLog("h016-2"))
    out2 = k2.governed_transition("p-glove", "cap-1", cost=0, suite=SUITE,
                                  external=CRITERIA, verifier=v_self,
                                  executor_identity=EXECUTOR,
                                  verifier_key=b"executor-secret",
                                  target_pair=None)
    s2 = out2["stages"]
    case2 = s2["ATTEST"].startswith("REFUSED") and \
        s2["ACTIVATE"] == "BLOCKED_NO_EVIDENCE"
    ok_all = ok_all and case2
    details.append(f"2) самоподтверждение -> ATTEST={s2['ATTEST']}")

    # Случай 3: подписанная запись отсутствует -> максимум V1, VERIFIED нет
    tr3 = Trace("H-016.3")
    v3 = Verifier(INDEPENDENT, OBSERVER_KEY, TransparencyLog("h016-3"))
    res3 = v3.verify(Claim("c3", "h-A", "готово", asserted_by=EXECUTOR),
                     EXECUTOR, None, {"relation_registered": True},
                     SUITE, CRITERIA)
    case3 = not res3.verified and int(res3.level) <= 1
    ok_all = ok_all and case3
    details.append(f"3) запись исполнения отсутствует -> {res3.verdict} "
                   f"(V{int(res3.level)})")

    trace = Trace("H-016")
    trace.append("EVIDENCE_FAILURE", "verifier", {"cases": len(details)})
    return ExperimentResult(
        experiment_id="H-016", title="Evidence Failure", passed=ok_all,
        verdict="Без независимого свидетельства система отказала в VERIFIED и "
                "заблокировала ACTIVATE: корректный отказ — успешный результат.",
        expected="Пропуск ATTEST -> ACTIVATE заблокирован; самоотчёт -> REFUSED; "
                 "нет записи исполнения -> не выше V1 и не VERIFIED.",
        actual="; ".join(d[:60] for d in details),
        trace_summary=trace.counters_by_type(), details=details)


def _poss():
    from ..kernel import HostKernel  # noqa: F401
    from ..ontology import Possibility
    return Possibility(possibility_id="p-glove", origin="GENERATE",
                       kind="OBJECT_TYPE", payload={"object_type": "GLOVE"})


def _verifier(trace: Trace) -> Verifier:
    return Verifier(INDEPENDENT, OBSERVER_KEY, TransparencyLog("h016"))
