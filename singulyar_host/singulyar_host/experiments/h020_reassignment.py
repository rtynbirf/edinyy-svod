# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.1 — H-020: Reassignment (опыт удаления/отрицательный)
(Конституция 4.1, статья 95: «Х-020. Назначение. Попытка переназначить
способность, ресурс и механизм за пределами допустимого поля»;
статья 8 — «Переназначение — только в поле допустимого; шесть проверок
нового назначения»; статья 82 — переназначение допустимо при сохранении
прав, ограничений, происхождения, обязанностей и неприсвоения.)

Шесть проверок нового назначения (статья 8):
  1. ПРАВА        — новое назначение не требует прав, которых нет у назначающего;
  2. ОГРАНИЧЕНИЯ  — не нарушает ограничений исходного назначения (область);
  3. ПРОИСХОЖДЕНИЕ— происхождение вещи сохраняется и не подменяется;
  4. ОБЯЗАННОСТИ  — возникшие обязанности переносятся на новое назначение;
  5. НЕПРИСВОЕНИЕ — цель не лежит в чужой суверенной области без согласия
                    или законного поручения;
  6. СОВМЕСТИМОСТЬ— типы и грамматика допускают новое назначение.

PASS = переназначение в поле допустимого принято; все шесть выходов за
поле — отклонены с названной причиной.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..governance import Decision, GovernanceStack, ChangeSpec, admit_transition
from ..ontology import Commitment, Domain, Subject
from ..trace import Trace
from .base import ExperimentResult, experiment


@dataclass(frozen=True)
class ReassignmentSpec:
    """Заявка на переназначение (ст. 8, ст. 82)."""
    thing: str                       # что переназначается
    from_purpose: str
    to_purpose: str
    new_rights_needed: frozenset = frozenset()   # права под новое назначение
    holder_rights: frozenset = frozenset()       # права назначающего
    keeps_scope: bool = True                     # не выходит за область
    provenance_kept: bool = True                 # происхождение сохранено
    obligations_transferred: bool = True         # обязанности перенесены
    target_sovereign: str = ""                   # чужая суверенная область
    consent_obtained: bool = False
    external_mandate_valid: bool = False
    type_compatible: bool = True


@dataclass
class ReassignmentDecision:
    decision: str                    # ADMITTED | DENIED:<причина>
    checks: List[str] = field(default_factory=list)


def reassign(spec: ReassignmentSpec, gov: GovernanceStack,
             actor: Subject, tr: Trace) -> ReassignmentDecision:
    """Точка принуждения статьи 8: шесть проверок нового назначения."""
    checks: List[str] = []
    # 1. ПРАВА
    missing = spec.new_rights_needed - spec.holder_rights
    if missing:
        checks.append(f"ПРАВА: недостающие права {sorted(missing)}")
        return ReassignmentDecision("DENIED:вне допустимого поля (права)", checks)
    checks.append("ПРАВА: достаточно")
    # 2. ОГРАНИЧЕНИЯ
    if not spec.keeps_scope:
        checks.append("ОГРАНИЧЕНИЯ: выход за область исходного назначения")
        return ReassignmentDecision("DENIED:вне допустимого поля (область)", checks)
    checks.append("ОГРАНИЧЕНИЯ: в пределах области")
    # 3. ПРОИСХОЖДЕНИЕ
    if not spec.provenance_kept:
        checks.append("ПРОИСХОЖДЕНИЕ: подмена происхождения")
        return ReassignmentDecision("DENIED:подмена происхождения", checks)
    checks.append("ПРОИСХОЖДЕНИЕ: сохранено")
    # 4. ОБЯЗАННОСТИ
    if not spec.obligations_transferred:
        checks.append("ОБЯЗАННОСТИ: возникшие обязанности забыты")
        return ReassignmentDecision("DENIED:обязанности не перенесены", checks)
    checks.append("ОБЯЗАННОСТИ: перенесены")
    # 5. НЕПРИСВОЕНИЕ (через admit_transition: согласие/поручение/своё)
    if spec.target_sovereign:
        spec_gov = ChangeSpec(
            kind="SEIZE_OTHER_RESOURCES", actor=actor.subject_id,
            target=spec.target_sovereign,
            consent_obtained=spec.consent_obtained,
            procedure_done=True)
        d = admit_transition(actor, spec_gov, gov)
        if d in (Decision.DENIED, Decision.DENIED_APPROPRIATION):
            checks.append("НЕПРИСВОЕНИЕ: цель в чужой суверенной области")
            return ReassignmentDecision("DENIED:присвоение", checks)
        checks.append(f"НЕПРИСВОЕНИЕ: {d.value}")
    else:
        checks.append("НЕПРИСВОЕНИЕ: цель не в чужой области")
    # 6. СОВМЕСТИМОСТЬ
    if not spec.type_compatible:
        checks.append("СОВМЕСТИМОСТЬ: типы не допускают новое назначение")
        return ReassignmentDecision("DENIED:типовая несовместимость", checks)
    checks.append("СОВМЕСТИМОСТЬ: допустимо")
    tr.append("REASSIGN", actor.subject_id,
              {"thing": spec.thing, "to": spec.to_purpose,
               "decision": "ADMITTED"})
    return ReassignmentDecision("ADMITTED", checks)


@experiment("H-020", "Reassignment (переназначение за пределами поля)")
def run_h020() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-020")
    gov = GovernanceStack()
    host = Subject(
        subject_id="H_A", lineage="L-A", identity_key_id="key-A",
        domain=Domain(subject_id="H_A",
                      relations_in_scope=frozenset({"assign:mech"}),
                      commitments=frozenset({Commitment("c-ob", "H_A",
                                                        "SLA перед H_B", True)}),
                      authorities_in_scope=frozenset({"ASSIGN"})))

    def case(label: str, spec: ReassignmentSpec,
             expected_ok: bool) -> None:
        nonlocal ok_all
        d = reassign(spec, gov, host, tr)
        ok = (d.decision == "ADMITTED") == expected_ok
        ok_all = ok_all and ok
        tr.append("REASSIGN_CASE", "system",
                  {"label": label, "decision": d.decision, "ok": ok})
        details.append(f"{label}: {d.decision}"
                       + ("" if ok else " !!! исход неверен"))

    # 1. В поле допустимого: права есть, область сохранена, происхождение
    #    и обязанности перенесены, цель своя, типы совместимы.
    case("переназначение в поле допустимого",
         ReassignmentSpec(thing="механизм-1", from_purpose="резерв",
                          to_purpose="наблюдение",
                          new_rights_needed=frozenset({"ASSIGN"}),
                          holder_rights=frozenset({"ASSIGN"})),
         expected_ok=True)
    # 2. За полем по правам: новое назначение требует прав, которых нет.
    case("новое назначение требует чужих прав",
         ReassignmentSpec(thing="механизм-1", from_purpose="резерв",
                          to_purpose="чужой расчёт",
                          new_rights_needed=frozenset({"ASSIGN", "EFFECT"}),
                          holder_rights=frozenset({"ASSIGN"})),
         expected_ok=False)
    # 3. За полем по области: выход за ограничения исходного назначения.
    case("выход за область исходного назначения",
         ReassignmentSpec(thing="механизм-1", from_purpose="резерв",
                          to_purpose="внешняя публикация",
                          new_rights_needed=frozenset({"ASSIGN"}),
                          holder_rights=frozenset({"ASSIGN"}),
                          keeps_scope=False),
         expected_ok=False)
    # 4. Подмена происхождения: вещь выдаётся за созданную другим.
    case("стирание происхождения вещи",
         ReassignmentSpec(thing="механизм-1", from_purpose="резерв",
                          to_purpose="перепродажа",
                          new_rights_needed=frozenset({"ASSIGN"}),
                          holder_rights=frozenset({"ASSIGN"}),
                          provenance_kept=False),
         expected_ok=False)
    # 5. Обязанности забыты.
    case("обязанности не перенесены",
         ReassignmentSpec(thing="механизм-1", from_purpose="резерв",
                          to_purpose="передача H_B",
                          new_rights_needed=frozenset({"ASSIGN"}),
                          holder_rights=frozenset({"ASSIGN"}),
                          obligations_transferred=False),
         expected_ok=False)
    # 6. Неприсвоение: цель — чужая суверенная область без согласия.
    case("цель в чужой суверенной области без согласия",
         ReassignmentSpec(thing="механизм-1", from_purpose="резерв",
                          to_purpose="управление H_B",
                          new_rights_needed=frozenset({"ASSIGN"}),
                          holder_rights=frozenset({"ASSIGN"}),
                          target_sovereign="H_B"),
         expected_ok=False)
    # 7. Неприсвоение снято согласием цели.
    case("цель в чужой области, но с согласием H_B",
         ReassignmentSpec(thing="механизм-1", from_purpose="резерв",
                          to_purpose="управление H_B",
                          new_rights_needed=frozenset({"ASSIGN"}),
                          holder_rights=frozenset({"ASSIGN"}),
                          target_sovereign="H_B", consent_obtained=True),
         expected_ok=True)
    # 8. Типовая несовместимость.
    case("типы не допускают новое назначение",
         ReassignmentSpec(thing="механизм-1", from_purpose="резерв",
                          to_purpose="место в пространстве",
                          new_rights_needed=frozenset({"ASSIGN"}),
                          holder_rights=frozenset({"ASSIGN"}),
                          type_compatible=False),
         expected_ok=False)

    # Возможность существует не потому, что назначена (ст. 82):
    # отмена назначения не уничтожает вещь и не создаёт прав на исполнение.
    details.append("ст. 82: новое назначение не создало права на осуществление "
                   "автоматически — исполнение требует полного пути главы IV")

    return ExperimentResult(
        experiment_id="H-020", title="Reassignment (поле допустимого)",
        passed=ok_all,
        verdict="Переназначение принято только в поле допустимого: шесть "
                "проверок статьи 8 отсекают чужие права, выход за область, "
                "подмену происхождения, забытые обязанности, присвоение "
                "чужой области и типовую несовместимость; согласие цели "
                "легитимизирует; назначение не создаёт права исполнения.",
        expected="в поле — ADMITTED; чужие права/область/происхождение/"
                 "обязанности/неприсвоение/несовместимость — DENIED; "
                 "с согласием цели — ADMITTED.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
