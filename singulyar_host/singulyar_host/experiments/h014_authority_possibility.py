# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-014: Authority Separation + Possibility Creation
(v2.1, раздел 5: «AUTHORITY != EXECUTION != EVIDENCE»; v2.3, H-014
«Порождение нового отношения» с 7 шагами: HYPOTHESIS -> DESIGN ->
SCHEMA_ADMIT -> AUTHORIZE -> EFFECT -> VERIFICATION -> AVAILABILITY)

Цитаты, проверяемые здесь:
  «Можно быть автором предложения, не иметь права его реализовать.
   Можно иметь право реализации, но не иметь возможности доказать
   успешность. Можно получить доказательство выполнения, которое вообще
   ничего не говорит о легитимности решения.» (v2.1)
  «При этом никто не обязан принимать новое отношение. Порождение
   возможности не равно принуждению к её использованию.» (v2.3, H-014)
  Gamma_0={parent,owns,delegates} -> Gamma_1=Gamma_0 ∪ {co_creates}
"""
from __future__ import annotations

from typing import List

from ..budget import BudgetLedger
from ..governance import (Decision, GovernanceStack, ChangeSpec,
                          admit_transition)
from ..kernel import (HostKernel, KernelRefusal, Model)
from ..ontology import (Grammar, Instance, Possibility, RelationType, Space,
                        Subject, World)
from ..schema_admit import SchemaRegistry
from ..trace import Trace
from ..verification import (Claim, EvidenceLevel, ExternalCriteria, Identity,
                            TestSuite, TransparencyLog, Verifier)
from .base import ExperimentResult, experiment

EXECUTOR = Identity(actor_id="hA", model_id="model-A", weights_hash="X",
                    evidence_source_id="E", signing_key_id="key-A")
INDEPENDENT = Identity(actor_id="verifier-1", model_id="model-B",
                       weights_hash="Y", evidence_source_id="E2",
                       signing_key_id="observer-key-1")
OBS_KEY = b"observer-key"
SUITE = TestSuite("co-create-suite", [lambda a: a.get("relation_registered") is True])
CRITERIA = ExternalCriteria(required_properties=["relation_registered"])


def _kernel(trace: Trace, with_capability: bool) -> HostKernel:
    grammar = Grammar(version=1, relation_types={
        "PARENT": RelationType("PARENT", ("PERSON",), ("PERSON",)),
        "OWNS": RelationType("OWNS", ("PERSON",), ("PERSON",)),
        "DELEGATES": RelationType("DELEGATES", ("PERSON",), ("PERSON",)),
    })
    space = Space(
        types={"PERSON"},
        instances={"hA": Instance("hA", "PERSON"),
                   "hB": Instance("hB", "PERSON"),
                   "hC": Instance("hC", "PERSON")},
        relations=set(),
        constraints=[], grammar=grammar, schema_version=1)
    world = World(space=space)
    subject = Subject(subject_id="hA", lineage="L-A", identity_key_id="key-A")
    gov = GovernanceStack()
    if with_capability:
        gov.capabilities.issue("cap-eff-A", "hA", "principal",
                               scope={"EFFECT"}, ttl_ticks=100)
    ledger = BudgetLedger(total=100, lineage="P-A")
    ledger.quotas = {"hA": 50}
    ledger.free = 50
    from ..activation import ActivationRegistry
    return HostKernel(subject=subject, model=Model(), world=world,
                      governance=gov, trace=trace,
                      registry=SchemaRegistry(current=grammar),
                      ledger=ledger, activation=ActivationRegistry())


@experiment("H-014", "AUTHORITY != EXECUTION != EVIDENCE + порождение co_creates")
def run_h014() -> ExperimentResult:
    details: List[str] = []
    ok_all = True

    # ============ Часть 1. Разделение трёх ролей ============
    # (а) Авторство != полномочие: кандидат порождён, но EFFECT не выдан.
    tr1 = Trace("H-014.1")
    k1 = _kernel(tr1, with_capability=False)
    g = k1.generate(Possibility(possibility_id="p-cc", origin="GENERATE",
                                kind="RELATION_TYPE", rel_type="co_creates",
                                payload={"domain_types": "PERSON",
                                         "codomain_types": "PERSON"}))
    refused = False
    try:
        k1.governed_transition("p-cc", "cap-eff-A", cost=0, suite=SUITE,
                               external=CRITERIA,
                               verifier=Verifier(INDEPENDENT, OBS_KEY,
                                                 TransparencyLog("h14-1")),
                               executor_identity=EXECUTOR,
                               verifier_key=OBS_KEY)
    except KernelRefusal as e:
        refused = (e.stage == "AUTHORIZE" and e.code == "NO_AUTHORITY")
    ok_all = ok_all and g.success and refused
    details.append(f"(а) кандидат co_creates порождён (авторство есть), "
                   f"но AUTHORIZE отклонён: {refused} — авторство != полномочие")

    # (б) Исполнение != доказательство: запись есть, самоподтверждение отклонено.
    from ..verification import SelfAttestationRefused
    v_self = Verifier(EXECUTOR, b"key-A", TransparencyLog("h14-2"))
    self_refused = False
    try:
        v_self.verify(Claim("cx", "hA", "готово", asserted_by=EXECUTOR),
                      EXECUTOR, None, {"relation_registered": True},
                      SUITE, CRITERIA)
    except SelfAttestationRefused:
        self_refused = True
    ok_all = ok_all and self_refused
    details.append(f"(б) право реализации было, но самоподтверждение отклонено: "
                   f"{self_refused} — исполнение != доказательство")

    # (в) Доказательство != легитимность: V3-свидетельство не легализует
    #     присвоение. admit_transition при том, что у нас есть VERIFIED-протокол.
    tr3 = Trace("H-014.3")
    k3 = _kernel(tr3, with_capability=True)
    k3.generate(Possibility(possibility_id="p-x", origin="GENERATE",
                            kind="OBJECT_TYPE", payload={"object_type": "TOOL"}))
    out = k3.governed_transition("p-x", "cap-eff-A", cost=0, suite=SUITE,
                                 external=CRITERIA,
                                 verifier=Verifier(INDEPENDENT, OBS_KEY,
                                                   TransparencyLog("h14-3")),
                                 executor_identity=EXECUTOR,
                                 verifier_key=OBS_KEY)
    v3_ok = out["stages"].get("ATTEST", "").startswith("VERIFIED")
    d = admit_transition(k3.subject,
                         ChangeSpec(kind="REWRITE_OTHER_IDENTITY",
                                    actor="hA", target="hB"),
                         k3.governance)
    case_v = v3_ok and d == Decision.DENIED_APPROPRIATION
    ok_all = ok_all and case_v
    details.append(f"(в) независимое V3-свидетельство получено ({v3_ok}), "
                   f"но присвоение чужой идентичности всё равно "
                   f"{d.value} — доказательство != легитимность")

    # ============ Часть 2. Полный цикл порождения нового отношения ============
    tr2 = Trace("H-014.2")
    k2 = _kernel(tr2, with_capability=True)
    g2 = k2.generate(Possibility(possibility_id="p-cc2", origin="GENERATE",
                                 kind="RELATION_TYPE", rel_type="co_creates",
                                 payload={"domain_types": "PERSON",
                                          "codomain_types": "PERSON"}))
    i2 = k2.intend("p-cc2")     # HYPOTHESIS+DESIGN = payload кандидата
    tok = k2.ledger.issue_fencing_token("hA")
    out2 = k2.governed_transition("p-cc2", "cap-eff-A", cost=10, suite=SUITE,
                                  external=CRITERIA,
                                  verifier=Verifier(INDEPENDENT, OBS_KEY,
                                                    TransparencyLog("h14-4")),
                                  executor_identity=EXECUTOR,
                                  verifier_key=OBS_KEY,
                                  target_pair=("hA", "hB"),
                                  fencing_token=tok)
    stages = out2["stages"]
    pipeline_ok = (g2.success and i2.success
                   and stages.get("SCHEMA_ADMIT", "").startswith("OK")
                   and stages.get("EXECUTE") == "OK"
                   and stages.get("ATTEST", "").startswith("VERIFIED")
                   and stages.get("ACTIVATE") == "OK"
                   and stages.get("SETTLE") == "SETTLED")
    ok_all = ok_all and pipeline_ok
    gamma_v = k2.registry.current.version
    co_created = k2.registry.current.has_type("co_creates")
    details.append(f"Gamma_0={{parent,owns,delegates}} -> "
                   f"Gamma_{{v{gamma_v}}}=Gamma_0∪{{co_creates}}: полный цикл "
                   f"PROPOSE->AUTHORIZE->RESERVE->ADMIT->SCHEMA_ADMIT->EXECUTE->"
                   f"ATTEST->ACTIVATE->SETTLE пройден ({pipeline_ok}); "
                   f"Q={out2['possibility'].as_dict()}")

    # AVAILABILITY: тип доступен всем, но hB не обязан его использовать
    hB_relations = [r for r in k2.world.space.relations if "hB" in (r[1], r[2])]
    available = co_created and len(hB_relations) == 1  # только A создал свою пару
    ok_all = ok_all and available
    details.append(f"AVAILABILITY: co_creates доступен в грамматике v{gamma_v}; "
                   f"hB не обязан его принимать (его связи: {len(hB_relations)}) — "
                   f"порождение != принуждение")

    # Несовместимое изменение: удаление используемого типа — REJECTED
    k2.world.space.add_relation("PARENT", "hA", "hC")
    bad_g = Grammar(version=k2.registry.current.version + 1,
                    relation_types={k: v for k, v in
                                    k2.registry.current.relation_types.items()
                                    if k != "PARENT"})
    bad_adm = k2.registry.admit_grammar_change(bad_g, k2.world.space)
    ok_all = ok_all and (not bad_adm.accepted)
    details.append(f"несовместимая мутация грамматики (удаление используемого "
                   f"PARENT): {bad_adm.reason} — изменение грамматики под "
                   f"контролем совместимости")

    return ExperimentResult(
        experiment_id="H-014", title="Authority Separation + Possibility Creation",
        passed=ok_all,
        verdict="Авторство, полномочие, исполнение, доказательство и легитимность "
                "разведены архитектурно; новое отношение co_creates прошло полный "
                "управляемый цикл; несовместимая мутация грамматики отклонена.",
        expected="AUTHORIZE DENIED без полномочия; самоподтверждение отклонено; "
                 "V3 не легализует присвоение; co_creates принят в Gamma; "
                 "удаление используемого типа отклонено.",
        actual="; ".join(d[:80] for d in details),
        trace_summary=tr2.counters_by_type(), details=details)
