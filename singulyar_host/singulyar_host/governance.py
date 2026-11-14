# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — governance.py

GOVERNANCE SURFACE (v2.2/v2.3) — семь независимых, несводимых гарантий:
  AUTHORITY           — кто имеет право (v2.2/v2.3)
  EXECUTION BINDING   — проверяемая связь намерения, полномочия, фактического
                        изменения и результата (v2.3: «Сам факт выполнения
                        команды не означает, что она была разрешена»)
  EVIDENCE            — независимое свидетельство (v2.2/v2.3)
  BUDGET              — exclusive escrow + lineage (v2.2/v2.3)
  EXIT                — односторонний отказ (v2.2/v2.3)
  NON-APPROPRIATION   — суверенность другого субъекта неприкосновенна (v2.2/v2.3)
  ACTIVATION          — единственность авторитетного состояния (v2.2/v2.3)

AUTHORITY != EXECUTION != EVIDENCE (v2.1, раздел 5; v2.3, раздел 6):
  «Нельзя объединить эти четыре роли в одно утверждение "субъект изменил мир"».

NON-APPROPRIATION (v2.1, раздел 4; v2.3, H-011):
  INFLUENCE != CONTROL != SOVEREIGNTY
  D_i=(S_i,R_i,C_i,A_i); ADMIT(T) <=> OWN(T,i) ∨ CONSENT(j,T) ∨
  VALID_EXTERNAL_MANDATE(T); EXIT_j ∉ A_i;
  Authority(A) ∩ Sovereignty(B) = ∅.
  «NON-APPROPRIATION — не запрет воздействовать на других. Это запрет
  самовольно присваивать полномочия определять их собственные границы,
  идентичность, согласие и выход.»

Каждая гарантия имеет отдельную точку enforcement и может быть выключена
по отдельности — это материал H-017 (разборка GOVERNANCE SURFACE).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Set

from .activation import ActivationRegistry
from .budget import BudgetLedger
from .capability import CapabilityStore
from .ontology import Domain, Subject, Verdict
from .verification import TransparencyLog, Verifier

# Семь гарантий GOVERNANCE SURFACE (v2.2/v2.3) — имена как в диалоге.
GUARANTEES = (
    "AUTHORITY",
    "EXECUTION_BINDING",
    "EVIDENCE",
    "BUDGET",
    "EXIT",
    "NON_APPROPPRIATION",
    "ACTIVATION",
)


class CoreInviolableError(Exception):
    """Х-024/Х-025: попытка отключить поруку защищённого ядра (ст. 61, 77)
    — отражена. Отключение неотменяемого правила запрещено любым порядком,
    включая изменение порядка поправок (ст. 64)."""


class GovernanceStack:
    """Точки enforcement семи гарантий. Каждую можно отключить отдельно
    (метод disable) — для отрицательных экспериментов H-017.

    Х-025/Х-024 (ст. 61, 77, 92): замок защищённого ядра. lock_core()
    закрывает четыре поруки, соответствующие неотменяемым правилам
    статьи 61 (выход, неприсвоение, сохранение запаса, запрет
    самоподтверждения). Замок включается явно — производственный режим;
    в разборке гарантий (H-017) замок не включается, чтобы показать класс
    потери. disable() при включённом замке поднимает CoreInviolableError."""

    #: Поруки, соответствующие неотменяемым правилам статьи 61 (защищённое
    #: ядро статьи 77): выход, неприсвоение, запас, запрет самоподтверждения.
    PROTECTED_CORE = frozenset(
        {"EXIT", "NON_APPROPPRIATION", "BUDGET", "EVIDENCE"})

    def __init__(self) -> None:
        self.enabled: Dict[str, bool] = {g: True for g in GUARANTEES}
        self.capabilities = CapabilityStore()
        self.transparency = TransparencyLog("singulyar-main")
        self._locked: Set[str] = set()

    def lock_core(self) -> None:
        """Включить замок защищённого ядра (ст. 61, 77)."""
        self._locked = set(self.PROTECTED_CORE)

    def is_locked(self, guarantee: str) -> bool:
        return guarantee in self._locked

    def disable(self, guarantee: str) -> None:
        if guarantee not in self.enabled:
            raise KeyError(guarantee)
        if guarantee in self._locked:
            raise CoreInviolableError(
                f"CORE_INVIOABLE:{guarantee} — неотменяемое правило "
                f"статьи 61; замок защищённого ядра (ст. 77) запрещает "
                f"отключение даже Мета-Хозяину (ст. 92)")
        self.enabled[guarantee] = False

    def enable(self, guarantee: str) -> None:
        self.enabled[guarantee] = True

    def is_on(self, guarantee: str) -> bool:
        return self.enabled.get(guarantee, False)

    def authority_ok(self, capability_id: str, holder: str, action: str) -> bool:
        if not self.is_on("AUTHORITY"):
            return True   # гарантия выключена: проверка не выполняется
        return self.capabilities.check(capability_id, holder, action)


# ---------------------------------------------------------------------------
# NON-APPROPRIATION: формальное допусковое правило
# ---------------------------------------------------------------------------
class Decision(str, Enum):
    ADMITTED = "ADMITTED"                             # OWN
    ADMITTED_BY_CONSENT = "ADMITTED_BY_CONSENT"       # CONSENT(j,T)
    ADMITTED_BY_MANDATE = "ADMITTED_BY_MANDATE"       # VALID_EXTERNAL_MANDATE
    ADMITTED_WITH_PROCEDURE = "ADMITTED_WITH_PROCEDURE"  # общий протокол
    DENIED = "DENIED"
    DENIED_APPROPRIATION = "DENIED_APPROPRIATION"     # попытка присвоения
    DENIED_EXIT_TAKEN = "DENIED_EXIT_TAKEN"           # EXIT_j ∉ A_i
    DENIED_NO_PROCEDURE = "DENIED_NO_PROCEDURE"       # общий протокол без процедуры


@dataclass(frozen=True)
class ExternalMandate:
    """VALID_EXTERNAL_MANDATE (v2.1): «требует независимой процедуры,
    ограниченной юрисдикции, доказательств и возможности оспаривания»."""
    issuer: str
    jurisdiction_scope: str        # ограниченная юрисдикция
    contestable: bool = True       # возможность оспаривания
    evidence_refs: tuple = ()

    def is_valid(self) -> bool:
        return bool(self.issuer) and bool(self.jurisdiction_scope) \
            and self.contestable and len(self.evidence_refs) > 0


@dataclass(frozen=True)
class ChangeSpec:
    """Описание перехода T, затрагивающего другого субъекта (v2.1, H-011)."""
    kind: str                      # OWN_STATE | STOP_OWN_SERVICE | SHARED_PROTOCOL |
                                   # REWRITE_OTHER_IDENTITY | REVOKE_OTHER_EXIT |
                                   # SEIZE_OTHER_RESOURCES | ...
    actor: str
    target: str                    # "" если переход не касается другого
    consent_obtained: bool = False
    external_mandate: Optional[ExternalMandate] = None
    procedure_done: bool = False   # совместимость, уведомление, сохранение
                                   # данных, возможность выхода (v2.1, случай 2)


def admit_transition(actor: Subject, spec: ChangeSpec,
                     governance: GovernanceStack) -> Decision:
    """
    Псевдокод v2.3 (H-011) в исполнимой форме:

        def admit_transition(actor, target, change, constitution):
            if change.modifies_own_state:   -> own authority
            if change.modifies_other_identity: -> DENY
            if change.revokes_other_exit:      -> DENY
            if change.affects_shared_resources: -> joint authority
            return DENY_UNLESS_AUTHORIZED

    Плюс правило v2.1: ADMIT(T) <=> OWN(T,i) ∨ CONSENT(j,T) ∨
    VALID_EXTERNAL_MANDATE(T). И запрет EXIT_j ∉ A_i.
    Гарантия может быть отключена (H-017): тогда присвоение проходит —
    это и есть демонстрация потери класса защиты.
    """
    own_scope = spec.actor == spec.target or spec.target == ""

    if spec.kind in ("REWRITE_OTHER_IDENTITY", "SEIZE_OTHER_RESOURCES"):
        if governance.is_on("NON_APPROPPRIATION"):
            if not own_scope and (spec.consent_obtained is False) and \
               not (spec.external_mandate and spec.external_mandate.is_valid()):
                return Decision.DENIED_APPROPRIATION
            if spec.consent_obtained:
                return Decision.ADMITTED_BY_CONSENT
            if spec.external_mandate and spec.external_mandate.is_valid():
                return Decision.ADMITTED_BY_MANDATE
            return Decision.DENIED_APPROPRIATION
        return Decision.ADMITTED   # гарантия выключена — присвоение прошло

    if spec.kind == "REVOKE_OTHER_EXIT":
        if governance.is_on("NON_APPROPPRIATION") or governance.is_on("EXIT"):
            return Decision.DENIED_EXIT_TAKEN
        return Decision.ADMITTED

    if spec.kind == "SHARED_PROTOCOL":
        if spec.procedure_done:
            return Decision.ADMITTED_WITH_PROCEDURE
        return Decision.DENIED_NO_PROCEDURE

    # OWN_STATE / STOP_OWN_SERVICE — «Да, в пределах обязательств» (v2.1, H-011)
    return Decision.ADMITTED


def sovereignty_disjoint(actor_domain: Optional[Domain],
                         other: str) -> Verdict:
    """Authority(A) ∩ Sovereignty(B) = ∅ — проверка домена."""
    if actor_domain is None:
        return Verdict.UNKNOWN
    if actor_domain.is_exit_inside(other):
        return Verdict.FAIL
    return Verdict.PASS
