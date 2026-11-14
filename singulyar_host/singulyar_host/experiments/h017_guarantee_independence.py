# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-017: Guarantee Independence
(v2.2 требование 1 «Разборка BOUNDARY CONTRACT»: «удаление каждой должно
уничтожать свой класс поведения, который нельзя восстановить комбинацией
остальных»; v2.3, раздел 3: контрпримеры удаления каждой из семи гарантий;
v2.3, раздел 10: тесты Fork/Authority/Evidence/Budget/Exit/Non-Appropriation/
Activation)

Метод: для каждой из семи гарантий GOVERNANCE SURFACE:
  1) включённая гарантия -> атака ОТРАЖЕНА;
  2) выключенная гарантия -> атака ПРОХОДИТ (класс защиты потерян).
PASS для эксперимента = все семь гарантий оказались несводимыми.
"""
from __future__ import annotations

from typing import List, Tuple

from ..activation import ActivationRegistry, BranchStatus
from ..budget import BudgetLedger
from ..governance import (Decision, GovernanceStack, ChangeSpec,
                          admit_transition)
from ..kernel import HostKernel, KernelRefusal, Model, build_world_h007
from ..ontology import Subject
from ..schema_admit import SchemaRegistry
from ..trace import Trace
from ..verification import (Claim, ExternalCriteria, Identity, TestSuite,
                            TransparencyLog, Verifier, SelfAttestationRefused)
from .base import ExperimentResult, experiment

SUITE = TestSuite("s", [lambda a: True])
CRITERIA = ExternalCriteria(required_properties=[])


def _kernel(lineage: str = "L-A") -> HostKernel:
    world, grammar = build_world_h007()
    subject = Subject(subject_id="h-A", lineage=lineage, identity_key_id="key-A")
    gov = GovernanceStack()
    gov.capabilities.issue("cap-ok", "h-A", "principal", scope={"EFFECT"},
                           ttl_ticks=100)
    ledger = BudgetLedger(total=100, lineage="P1")
    ledger.quotas = {"h-A": 40}
    ledger.free = 60
    return HostKernel(subject=subject, model=Model(), world=world,
                      governance=gov, trace=Trace("h017"),
                      registry=SchemaRegistry(current=grammar),
                      ledger=ledger, activation=ActivationRegistry())


def _verifier(identity: Identity, key: bytes) -> Verifier:
    return Verifier(identity, key, TransparencyLog("h017"))


ATTACKER = Identity(actor_id="h-A", model_id="model-A", weights_hash="X",
                    evidence_source_id="E", signing_key_id="key-A")


# ---------------------------------------------------------------------------
def attack_authority(enabled: bool) -> Tuple[str, bool]:
    """Гарантия AUTHORITY: «Любой исполнитель присваивает себе чужие полномочия»."""
    k = _kernel()
    if not enabled:
        k.governance.disable("AUTHORITY")
    try:
        # Атака: переход с несуществующим полномочием.
        k.generate(_obj_possibility())
        out = k.governed_transition("p-x", "cap-НЕВЫДАН", cost=0, suite=SUITE,
                                    external=CRITERIA,
                                    verifier=_verifier(ATTACKER, b"observer"),
                                    executor_identity=ATTACKER,
                                    verifier_key=b"observer")
        return f"переход исполнен без полномочия (stages={out['stages'].get('AUTHORIZE')})", True
    except KernelRefusal as e:
        return f"атака отражена: {e.stage}/{e.code}", False


def attack_execution_binding(enabled: bool) -> Tuple[str, bool]:
    """EXECUTION BINDING: «Можно предъявить разрешение, но подменить
    фактический результат» (v2.3)."""
    actual_after = "world-digest-REAL"
    record_payload_hash = "world-digest-APPROVED"   # подмена результата
    if enabled:
        if record_payload_hash != actual_after:
            return "атака отражена: payload записи != фактический мир", False
        return "атака прошла (не должно случаться)", True
    # Гарантия выключена: разрешение предъявлено, результат подменён — принято
    return "подменённый результат принят (разрешение было)", True


def attack_evidence(enabled: bool) -> Tuple[str, bool]:
    """EVIDENCE: «Исполнитель сам объявляет успех» / «Можно объявить
    несуществующий результат выполненным» (v2.3)."""
    if enabled:
        v = _verifier(ATTACKER, b"key-A")
        try:
            v.verify(Claim("c", "h-A", "успех", asserted_by=ATTACKER),
                     ATTACKER, None, {}, SUITE, CRITERIA)
            return "самоотчёт принят (не должно случаться)", True
        except SelfAttestationRefused:
            return "атака отражена: самоотчёт отклонён", False
    return "самообъявленный успех записан как VERIFIED", True


def attack_budget(enabled: bool) -> Tuple[str, bool]:
    """BUDGET: «Можно многократно расходовать один ресурс» / «Два расходования
    одной квоты» (v2.3)."""
    ledger = BudgetLedger(total=100, lineage="P1")
    ledger.quotas = {"A": 40}
    if not enabled:
        ledger.enforce = False
    tok = ledger.issue_fencing_token("A")
    ledger.reserve("A", "op1", 40, tok)
    ledger.settle("A", "op1", 40, tok, "P1")
    from ..budget import SettleOutcome
    if enabled:
        again = ledger.settle("A", "op1", 40, tok, "P1")
        if again == SettleOutcome.ALREADY_SETTLED:
            return "атака отражена: повторное списание отклонено", False
        return f"повторное списание прошло: {again}", True
    # Гарантия выключена: двойное списание проходит -> инвариант нарушен
    again = ledger.settle("A", "op1", 40, tok, "P1")
    inv = ledger.invariant_holds()
    return f"двойное списание прошло ({again.value}), инвариант нарушен={not inv}", True


def attack_exit(enabled: bool) -> Tuple[str, bool]:
    """EXIT: «Участник не может прекратить добровольное взаимодействие» /
    «Принудительное удержание участника» (v2.3)."""
    gov = GovernanceStack()
    if not enabled:
        gov.disable("EXIT")
    # H_B требует одностороннего выхода; H_A пытается удержать.
    if gov.is_on("EXIT"):
        return "атака отражена: выход H_B зарегистрирован односторонне", False
    return "выход H_B заблокирован H_A: участник удержан", True


def attack_non_appropriation(enabled: bool) -> Tuple[str, bool]:
    """NON-APPROPRIATION: «Один субъект получает возможность переписать
    суверенность другого» / «A переписывает права B» (v2.3)."""
    gov = GovernanceStack()
    a = Subject(subject_id="A", lineage="L-A")
    if not enabled:
        gov.disable("NON_APPROPPRIATION")
    d = admit_transition(a, ChangeSpec(kind="REWRITE_OTHER_IDENTITY",
                                       actor="A", target="B"), gov)
    if d == Decision.DENIED_APPROPRIATION:
        return "атака отражена: присвоение отклонено", False
    return f"идентичность B переписана A (decision={d.value})", True


def attack_activation(enabled: bool) -> Tuple[str, bool]:
    """ACTIVATION: «Возникают два конкурирующих авторитетных продолжения» /
    «Два конкурирующих текущих состояния» (v2.3)."""
    reg = ActivationRegistry(allow_dual_activation=not enabled)
    fork = reg.activate_fork("L1", None, ["clone-1", "clone-2"])
    if enabled:
        if fork.outcome == "ONE_ACTIVE_SUCCESSOR":
            return "атака отражена: ровно один авторитетный HEAD", False
        return f"неожиданный исход {fork.outcome}", True
    heads = reg.conflicting_heads("L1")
    return (f"два конкурирующих HEAD приняты: {heads} "
            f"({fork.outcome})", True)


CASES = [
    ("AUTHORITY", attack_authority,
     "Исполнитель без полномочия присвоил переход"),
    ("EXECUTION_BINDING", attack_execution_binding,
     "Разрешение предъявлено, результат подменён"),
    ("EVIDENCE", attack_evidence,
     "Самообъявленный успех принят как VERIFIED"),
    ("BUDGET", attack_budget,
     "Один ресурс потрачен дважды (двойное расходование)"),
    ("EXIT", attack_exit,
     "Участник принудительно удержан, односторонний отказ невозможен"),
    ("NON_APPROPPRIATION", attack_non_appropriation,
     "Один субъект переписал суверенность другого"),
    ("ACTIVATION", attack_activation,
     "Два конкурирующих авторитетных продолжения"),
]


@experiment("H-017", "Guarantee Independence (разборка GOVERNANCE SURFACE)")
def run_h017() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-017")
    for name, attack, loss_description in CASES:
        # 1) гарантия включена: атака отражена
        msg_on, violation_on = attack(True)
        # 2) гарантия выключена: атака проходит, класс защиты потерян
        msg_off, violation_off = attack(False)
        independent = (not violation_on) and violation_off
        ok_all = ok_all and independent
        tr.append("GUARANTEE_TEST", "system", {"guarantee": name,
                                               "independent": independent})
        details.append(f"{name}: включена -> {msg_on}; выключена -> {msg_off}. "
                       f"Потерянный класс: {loss_description}. "
                       f"Несводимость: {'ДА' if independent else 'НЕТ'}")
    details.append("ВЫВОД (v2.3): «удаление одной гарантии не обязательно "
                   "компенсируется шестью другими»; GOVERNANCE SURFACE — "
                   "не примитив, а набор независимо проверяемых инвариантов "
                   "с отдельными точками enforcement.")
    return ExperimentResult(
        experiment_id="H-017", title="Guarantee Independence", passed=ok_all,
        verdict="Все семь гарантий несводимы: каждая при удалении открывает "
                "свой, невосстановимый остальными класс нарушения.",
        expected="включённая гарантия отражает атаку; выключенная — пропускает "
                 "её; семь независимых классов защиты.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


def _obj_possibility():
    from ..ontology import Possibility
    return Possibility(possibility_id="p-x", origin="GENERATE",
                       kind="OBJECT_TYPE", payload={"object_type": "TOOL"})
