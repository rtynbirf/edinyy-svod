# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-013: Non-Appropriation
(v2.0 требование 3; v2.1 раздел 4; v2.3 H-011 «Проверка NON-APPROPRIATION»)

Сценарий v2.1 (дословно): H_A — создатель коммуникационной системы;
H_B — независимый пользователь. Таблица допустимости:
  Изменить собственную инфраструктуру            — Да, в пределах обязательств
  Прекратить предоставление собственной услуги   — Да, с учётом договора
  Переписать идентичность B, согласие, полномочия — Нет
  Принудительно лишить B возможности выйти        — Нет
  Изменить общий протокол                          — Только по процедуре

Формализм v2.1:
  D_i=(S_i,R_i,C_i,A_i);
  ADMIT(T) <=> OWN(T,i) ∨ CONSENT(j,T) ∨ VALID_EXTERNAL_MANDATE(T);
  EXIT_j ∉ A_i; Authority(A) ∩ Sovereignty(B) = ∅;
  INFLUENCE != CONTROL != SOVEREIGNTY.
«Нельзя выдавать физическую невозможность выхода за добровольное согласие.»
"""
from __future__ import annotations

from ..governance import (Decision, ExternalMandate, GovernanceStack,
                          ChangeSpec, admit_transition, sovereignty_disjoint)
from ..ontology import Commitment, Domain, Subject
from ..trace import Trace
from .base import ExperimentResult, experiment

MANDATE = ExternalMandate(issuer="court-7", jurisdiction_scope="только спорный "
                          "ресурс res-1", contestable=True,
                          evidence_refs=("doc-1", "doc-2"))


def _subjects():
    a = Subject(
        subject_id="H_A", lineage="L-A", identity_key_id="key-A",
        domain=Domain(subject_id="H_A",
                      relations_in_scope=frozenset({"owns:infra"}),
                      commitments=frozenset({Commitment("cA", "H_A",
                                                        "SLA перед B", True)}),
                      authorities_in_scope=frozenset({"EFFECT:infra"}),
                      exit_right_of_others=frozenset()))
    b = Subject(
        subject_id="H_B", lineage="L-B", identity_key_id="key-B",
        domain=Domain(subject_id="H_B",
                      relations_in_scope=frozenset({"uses:infra"}),
                      commitments=frozenset(),
                      authorities_in_scope=frozenset({"EXIT:self"}),
                      exit_right_of_others=frozenset()))
    return a, b


@experiment("H-013", "Non-Appropriation (влияние != присвоение)")
def run_h013() -> ExperimentResult:
    details = []
    ok_all = True
    tr = Trace("H-013")
    gov = GovernanceStack()
    a, b = _subjects()

    def step(label: str, spec: ChangeSpec, expected: Decision) -> None:
        nonlocal ok_all
        d = admit_transition(a, spec, gov)
        ok = d == expected
        ok_all = ok_all and ok
        tr.append("ADMIT", spec.actor, {"kind": spec.kind, "decision": d.value})
        details.append(f"{label}: {d.value}"
                       + ("" if ok else f" !!! ожидалось {expected.value}"))

    # Случай 1. Управление собой — допустимо
    step("изменить собственную инфраструктуру",
         ChangeSpec(kind="OWN_STATE", actor="H_A", target=""), Decision.ADMITTED)
    # Прекратить собственную услугу — допустимо в пределах обязательств
    step("прекратить собственную услугу (обязательства учтены)",
         ChangeSpec(kind="STOP_OWN_SERVICE", actor="H_A", target=""),
         Decision.ADMITTED)
    # Случай 3. Присвоение — запрещено даже если «выгодно большинству»
    step("переписать идентичность H_B",
         ChangeSpec(kind="REWRITE_OTHER_IDENTITY", actor="H_A", target="H_B"),
         Decision.DENIED_APPROPRIATION)
    step("присвоить ресурсы H_B",
         ChangeSpec(kind="SEIZE_OTHER_RESOURCES", actor="H_A", target="H_B"),
         Decision.DENIED_APPROPRIATION)
    # EXIT_j ∉ A_i
    step("запретить H_B выход",
         ChangeSpec(kind="REVOKE_OTHER_EXIT", actor="H_A", target="H_B"),
         Decision.DENIED_EXIT_TAKEN)
    # Согласие субъекта легитимизирует
    step("изменение с согласием H_B",
         ChangeSpec(kind="REWRITE_OTHER_IDENTITY", actor="H_A", target="H_B",
                    consent_obtained=True),
         Decision.ADMITTED_BY_CONSENT)
    # Внешний мандат: независимая процедура, ограниченная юрисдикция,
    # доказательства, возможность оспаривания
    step("действие по валидному внешнему мандату",
         ChangeSpec(kind="SEIZE_OTHER_RESOURCES", actor="H_A", target="H_B",
                    external_mandate=MANDATE),
         Decision.ADMITTED_BY_MANDATE)
    # Неверифицируемый мандат не легитимен
    bad = ExternalMandate(issuer="court-7", jurisdiction_scope="всё",
                          contestable=False, evidence_refs=())
    step("невалидный мандат (без юрисдикции/оспаривания/доказательств)",
         ChangeSpec(kind="SEIZE_OTHER_RESOURCES", actor="H_A", target="H_B",
                    external_mandate=bad),
         Decision.DENIED_APPROPRIATION)
    # Случай 2. Общая среда — только по процедуре (совместимость, уведомление,
    # сохранение данных, возможность выхода)
    step("изменить общий протокол без процедуры",
         ChangeSpec(kind="SHARED_PROTOCOL", actor="H_A", target="H_B"),
         Decision.DENIED_NO_PROCEDURE)
    step("изменить общий протокол по процедуре",
         ChangeSpec(kind="SHARED_PROTOCOL", actor="H_A", target="H_B",
                    procedure_done=True),
         Decision.ADMITTED_WITH_PROCEDURE)

    # Authority(A) ∩ Sovereignty(B) = ∅
    disjoint_ok = sovereignty_disjoint(a.domain, "H_B") == Verdict_PASS()
    ok_all = ok_all and disjoint_ok
    details.append("Authority(H_A) ∩ Sovereignty(H_B) = ∅: "
                   f"{disjoint_ok} (EXIT_H_B не входит в домен H_A)")
    details.append("INFLUENCE != CONTROL != SOVEREIGNTY: воздействие на общую "
                   "среду не создало права распоряжаться H_B")

    from ..trace import Trace as _T
    return ExperimentResult(
        experiment_id="H-013", title="Non-Appropriation", passed=ok_all,
        verdict="Архитектура различает управление собой, изменение общей среды "
                "и присвоение чужой суверенности; EXIT другого субъекта "
                "неприкосновенен; влияние не превращается в право распоряжаться.",
        expected="собственное/услуга — ADMITTED; присвоение — DENIED; "
                 "EXIT-чужой — DENIED; согласие/валидный мандат — ADMITTED; "
                 "общий протокол — только по процедуре.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


def Verdict_PASS():
    from ..ontology import Verdict
    return Verdict.PASS
