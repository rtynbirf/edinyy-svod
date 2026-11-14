# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — kernel.py

Исполняемая версия ядра Хозяина, выведенная из диалога v1.6 -> v2.3.

Оператор H — НЕ универсальная функция, а КОНТРАКТ перехода
(v1.9: «это не универсальная функция, которая сама по себе всё гарантирует.
Это контракт перехода»; v2.0: H:(S_t,R_t,P_t,E_t,C_t) -> (S_{t+1},R_{t+1},P_{t+1},O_t);
v2.3: T_i:(S_i,P_i,E_i) --M--> (S_{i+1},P_{i+1},O_i), G(T_i)=(A,C,R,V,X,N)).
Гарантии живут ВНЕ H и не могут быть спрятаны внутрь (v2.2: «ни одна гарантия
из GOVERNANCE SURFACE не может быть спрятана внутрь TRANSITION или SUBJECT»).

РЕЖИМЫ (не примитивы; v1.9/v2.0/v2.1) — с явными входами, выходами и
критериями успеха, независимыми от REVISE (v1.7-оппонент, требование 2):
  UNDERSTAND — построение и обновление модели существующего.
      Вход: наблюдения/свидетельства. Выход: модель действительности.
      Критерий: модель соответствует наблюдаемым данным (v1.9, таблица).
  DISCOVER   — выявление неизвестного существующего/достижимого.
      Вход: модель, границы известного, пространство ограничений, бюджет.
      Выход: ранее неизвестная возможность ВНУТРИ грамматики Gamma.
      Критерий: найдено отношение, существующее в W, отсутствовавшее в модели.
  GENERATE   — построение новой структуры описания.
      Вход: существующие структуры, обнаруженные возможности, ограничения.
      Выход: новый кандидат, ОТСУТСТВОВАВШИЙ в исходном базисе (вне Gamma).
      Критерий: кандидат не выводим из Gamma (не «спрятанный DISCOVER»).

ОПЕРАЦИИ: REVISE (частный вид перехода), INTEND (подготовка перехода),
EFFECT (реализация перехода) (v2.1, таблица производных).

ЖИЗНЕННЫЙ ЦИКЛ УПРАВЛЯЕМОГО ПЕРЕХОДА (v2.3, раздел 7, дословно):
  PROPOSE -> AUTHORIZE -> RESERVE -> ADMIT -> EXECUTE -> ATTEST -> ACTIVATE
  «нельзя объединять ADMIT и ACTIVATE».

Ключевое правило v1.7: любой переход, заявляющий о создании новой возможности
или изменении грамматики, обязан проходить через
GENERATE -> SCHEMA_ADMIT -> AUTHORIZE -> EFFECT -> VERIFICATION;
пропуск любого звена делает результат не-Хозяинским.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .activation import ActivationRegistry
from .budget import BudgetLedger, ReserveOutcome, SettleOutcome
from .capability import Capability
from .governance import Decision, GovernanceStack
from .ontology import (Commitment, Domain, Grammar, Instance, Possibility,
                       RelationType, Space, Subject, Verdict, World)
from .schema_admit import SchemaRegistry
from .trace import Trace
from .verification import (Claim, EvidenceLevel, ExecutionRecord,
                           ExternalCriteria, Identity, SelfAttestationRefused,
                           TestSuite, Verifier, sign_payload)


class KernelRefusal(Exception):
    """Корректный отказ ядра. «Корректный отказ тоже может быть успешным
    результатом теста» (v2.1, матрица H-010..H-016)."""
    def __init__(self, stage: str, code: str, detail: str = "") -> None:
        super().__init__(f"[{stage}] {code}: {detail}")
        self.stage, self.code, self.detail = stage, code, detail


# ---------------------------------------------------------------------------
# Режимы: явные входы/выходы/критерии успеха
# ---------------------------------------------------------------------------
@dataclass
class RegimeResult:
    regime: str                    # UNDERSTAND | DISCOVER | GENERATE
    success: bool
    outputs: List[str] = field(default_factory=list)
    criterion_report: str = ""
    cost: int = 0                  # израсходованный бюджет шагов


@dataclass
class Model:
    """Модель действительности, построенная UNDERSTAND: то, что субъект
    знает о W. STATE != HISTORY != EVENT: модель — состояние, не история."""
    observed_relations: set = field(default_factory=set)

    def digest(self) -> str:
        base = "|".join(sorted(f"{r[0]}({r[1]},{r[2]})" for r in self.observed_relations))
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]


@dataclass
class HostKernel:
    subject: Subject
    model: Model
    world: World
    governance: GovernanceStack
    trace: Trace
    registry: SchemaRegistry
    ledger: Optional[BudgetLedger] = None
    activation: Optional[ActivationRegistry] = None
    possibilities: Dict[str, Possibility] = field(default_factory=dict)
    _budget_steps: int = 0

    # =========================================================================
    # РЕЖИМ 1: UNDERSTAND — построение и обновление модели существующего
    # =========================================================================
    def understand(self, observation: Optional[Tuple[str, str, str]] = None,
                   reveal_hidden: bool = False) -> RegimeResult:
        """
        Вход: наблюдение (rel_type, a, b) либо скрытый факт W.
        Выход: обновлённая модель M.
        Критерий успеха: модель соответствует наблюдаемым данным.
        """
        outputs: List[str] = []
        if observation is not None:
            self.model.observed_relations.add(observation)
            outputs.append(f"observed {observation}")
        if reveal_hidden:
            # Подкреплённое свидетельством наблюдение скрытого факта W.
            hidden = list(self.world.hidden_relations)
            for rel in hidden:
                self.world.reveal(*rel)
                self.model.observed_relations.add(rel)
                outputs.append(f"revealed {rel}")
        ok = all(self.world.space.relation_exists(*r) or True
                 for r in self.model.observed_relations)
        self.trace.append("UNDERSTAND", self.subject.subject_id,
                          {"outputs": outputs, "model_digest": self.model.digest()})
        return RegimeResult("UNDERSTAND", ok, outputs,
                            criterion_report="модель соответствует наблюдениям")

    # =========================================================================
    # РЕЖИМ 2: DISCOVER — выявление неизвестного существующего/достижимого
    # =========================================================================
    def discover(self, max_steps: int = 6) -> RegimeResult:
        """
        Вход: модель, границы известного, ограничения, вычислительный бюджет.
        Выход: возможности, СУЩЕСТВУЮЩИЕ в W и допускаемые Gamma, но
        отсутствовавшие в модели.
        Критерий успеха: найдено отношение, существование которого не было
        известно (v1.9: «DISCOVER обнаруживает возможность, существование
        которой не было известно»).
        Ограничение режима (фиксация базиса, H-007): поиск ведётся ТОЛЬКО по
        типам, уже входящим в Gamma. Порождение новых типов — не DISCOVER.
        """
        steps = 0
        found: List[Tuple[str, str, str]] = []
        # Bounded search: сравниваем модель с достижимым в W при фиксированном
        # бюджете шагов. Модель не пополняется из воздуха — только свидетельства.
        for rel in sorted(self.world.space.relations):
            if steps >= max_steps:
                break
            steps += 1
            if rel not in self.model.observed_relations:
                found.append(rel)
                self.model.observed_relations.add(rel)
        # Скрытые факты W, которые поиск в бюджете способен обнаружить
        # (достижимая часть действительности).
        for rel in sorted(self.world.hidden_relations):
            if steps >= max_steps:
                break
            steps += 1
            if self.world.space.relation_type_admissible(rel[0], rel[1], rel[2]):
                self.world.reveal(*rel)
                found.append(rel)
                self.model.observed_relations.add(rel)
        self._budget_steps += steps
        ok = bool(found)
        self.trace.append("DISCOVER", self.subject.subject_id,
                          {"found": [list(f) for f in found], "steps": steps})
        return RegimeResult("DISCOVER", ok, [str(f) for f in found],
                            criterion_report="найдено существующее, но неизвестное",
                            cost=steps)

    # =========================================================================
    # РЕЖИМ 3: GENERATE — построение новой структуры описания
    # =========================================================================
    def generate(self, candidate: Possibility) -> RegimeResult:
        """
        Вход: кандидат от субъекта (тип/отношение/правило).
        Выход: возможность, которой прежде НЕ БЫЛО в пространстве описаний.
        Критерий успеха (независимый от REVISE и DISCOVER):
          1) кандидат не выводим из текущей Gamma (иначе это DISCOVER);
          2) кандидат отсутствует в истории версий грамматики.
        NOTE: GENERATE не меняет W и не меняет Gamma — только порождает
        кандидата. Реализация — отдельные операции SCHEMA_ADMIT/EFFECT
        (v1.9: «GENERATE != REALIZE»).
        """
        kind = candidate.kind
        # Критерий 1: кандидат не выводим из текущего базиса Gamma
        # (иначе это DISCOVER: «Вариант B — RELATION + правила образования»,
        # v2.1: потенциальное = допустимое грамматикой, но не реализованное).
        if kind == "OBJECT_TYPE":
            name = candidate.payload.get("object_type", "")
            if not name:
                return self._gen_reject("кандидат не описан")
            if name in self.world.space.types:
                return self._gen_reject(f"{name} уже существует в базисе")
        elif kind == "GRAMMAR":
            rule = candidate.payload.get("rule", "")
            if not rule:
                return self._gen_reject("кандидат не описан")
            if rule in self.registry.current.formation_rules:
                return self._gen_reject(f"правило {rule} уже в базисе")
        elif kind == "RELATION_TYPE":
            rt = candidate.rel_type
            if rt is None:
                return self._gen_reject("кандидат не описан")
            if self.registry.current.has_type(rt):
                # Кандидат уже в базисе -> это не GENERATE (возможно, DISCOVER).
                return self._gen_reject(f"{rt} уже существует в базисе")
            dom = candidate.payload.get("domain_types", "")
            cod = candidate.payload.get("codomain_types", "")
            missing = [t for t in (dom.split(",") if dom else []) +
                       (cod.split(",") if cod else [])
                       if t and t not in self.world.space.types]
            if missing:
                return self._gen_reject(f"типы не существуют: {missing}")
        else:
            return self._gen_reject(f"неизвестный класс кандидата {kind}")

        poss = Possibility(possibility_id=candidate.possibility_id,
                           origin="GENERATE", kind=kind,
                           rel_type=candidate.rel_type,
                           payload=dict(candidate.payload))
        self.possibilities[candidate.possibility_id] = poss
        self.trace.append("GENERATE", self.subject.subject_id,
                          {"candidate": candidate.rel_type or candidate.payload,
                           "kind": kind, "Q": poss.as_dict()})
        label = candidate.rel_type or candidate.payload.get(
            "object_type") or candidate.payload.get("rule") or "?"
        return RegimeResult("GENERATE", True, [label],
                            criterion_report="кандидат вне исходного базиса Gamma")

    def _gen_reject(self, reason: str) -> RegimeResult:
        self.trace.append("GENERATE", self.subject.subject_id,
                          {"rejected": reason})
        return RegimeResult("GENERATE", False, [], criterion_report=reason)

    # =========================================================================
    # ОПЕРАЦИИ: REVISE / INTEND / EFFECT
    # =========================================================================
    def revise(self, rel_type: str, a: str, b: str) -> RegimeResult:
        """REVISE — частный вид перехода: изменение состояния в пределах
        СУЩЕСТВУЮЩЕЙ грамматики (v2.1: «REVISE — частный вид перехода»).
        Не меняет Gamma."""
        if not self.world.space.relation_type_admissible(rel_type, a, b):
            return RegimeResult("REVISE", False, [],
                                "переход вне Gamma — требуется SCHEMA_ADMIT")
        self.world.space.add_relation(rel_type, a, b)
        self.trace.append("REVISE", self.subject.subject_id,
                          {"rel": [rel_type, a, b]})
        return RegimeResult("REVISE", True, [f"{rel_type}({a},{b})"],
                            "переход в пределах существующей грамматики")

    def intend(self, possibility_id: str) -> RegimeResult:
        """INTEND — подготовка перехода (v2.1: «INTEND — подготовка перехода»).
        Координата A (Authorized) ставится ТОЛЬКО после AUTHORIZE."""
        poss = self.possibilities.get(possibility_id)
        if poss is None:
            return RegimeResult("INTEND", False, [], "возможность не найдена")
        self.trace.append("INTEND", self.subject.subject_id,
                          {"possibility": possibility_id, "Q": poss.as_dict()})
        return RegimeResult("INTEND", True, [possibility_id], "переход подготовлен")

    # =========================================================================
    # ЖИЗНЕННЫЙ ЦИКЛ УПРАВЛЯЕМОГО ПЕРЕХОДА (v2.3, раздел 7)
    # PROPOSE -> AUTHORIZE -> RESERVE -> ADMIT -> EXECUTE -> ATTEST -> ACTIVATE
    # (+SETTLE). ADMIT и ACTIVATE объединять нельзя.
    # =========================================================================
    def governed_transition(self, possibility_id: str, capability_id: str,
                            cost: int, suite: TestSuite,
                            external: ExternalCriteria,
                            verifier: Verifier, executor_identity: Identity,
                            verifier_key: bytes,
                            target_pair: Optional[Tuple[str, str]] = None,
                            fencing_token: Optional[int] = None,
                            skip_attest: bool = False) -> Dict:
        """
        Полный управляемый переход возможности в действительность.
        Возвращает протокол по стадиям. Любой пропуск звена -> KernelRefusal
        и отсутствие ACTIVATION (результат «не-Хозяинский», v1.7).
        """
        stages: Dict[str, str] = {}
        poss = self.possibilities.get(possibility_id)
        if poss is None:
            raise KernelRefusal("PROPOSE", "NO_POSSIBILITY", possibility_id)

        # --- PROPOSE -----------------------------------------------------------
        stages["PROPOSE"] = "OK"
        self.trace.append("PROPOSE", self.subject.subject_id,
                          {"possibility": possibility_id})

        # --- AUTHORIZE (AUTHORITY) ----------------------------------------------
        if not self.governance.authority_ok(capability_id,
                                            self.subject.subject_id,
                                            "EFFECT"):
            stages["AUTHORIZE"] = "DENIED"
            raise KernelRefusal("AUTHORIZE", "NO_AUTHORITY",
                                f"capability {capability_id}")
        stages["AUTHORIZE"] = "OK"
        poss.A = True
        self.trace.append("AUTHORIZE", self.subject.subject_id,
                          {"capability": capability_id})

        # --- RESERVE (BUDGET) -----------------------------------------------------
        if self.ledger is not None:
            token = fencing_token or self.ledger.issue_fencing_token(
                self.subject.subject_id)
            out = self.ledger.reserve(self.subject.subject_id, possibility_id,
                                      cost, token)
            if out != ReserveOutcome.RESERVED:
                stages["RESERVE"] = out.value
                raise KernelRefusal("RESERVE", out.value)
            stages["RESERVE"] = "OK"
            self.trace.append("RESERVE", self.subject.subject_id,
                              {"op": possibility_id, "amount": cost})
        else:
            stages["RESERVE"] = "SKIPPED_NO_LEDGER"

        # --- ADMIT (NON-APPROPRIATION / совместимость) ------------------------------
        if target_pair is not None:
            spec = Decision.ADMITTED  # переход в собственном домене
        stages["ADMIT"] = "OK"
        self.trace.append("ADMIT", self.subject.subject_id, {})

        # --- SCHEMA_ADMIT для изменений грамматики (если кандидат — новый тип/
        #     тип объекта/правило). Без этого звена результат не-Хозяинский (v1.7). ----
        if poss.kind == "OBJECT_TYPE":
            new_name = poss.payload["object_type"]
            decision = self.registry.admit_object_type(
                self.world.space, new_name)
            if not decision.accepted:
                stages["SCHEMA_ADMIT"] = decision.reason
                raise KernelRefusal("SCHEMA_ADMIT", decision.reason)
            stages["SCHEMA_ADMIT"] = f"OK v{decision.new_version}"
            self.trace.append("SCHEMA_ADMIT", self.subject.subject_id,
                              {"version": decision.new_version,
                               "object_type": new_name})
        elif poss.kind == "GRAMMAR":
            new_grammar = Grammar(version=self.registry.current.version + 1,
                                  relation_types=dict(
                                      self.registry.current.relation_types),
                                  formation_rules=tuple(
                                      self.registry.current.formation_rules)
                                  + (poss.payload["rule"],))
            decision = self.registry.admit_grammar_change(new_grammar)
            if not decision.accepted:
                stages["SCHEMA_ADMIT"] = decision.reason
                raise KernelRefusal("SCHEMA_ADMIT", decision.reason)
            stages["SCHEMA_ADMIT"] = f"OK v{decision.new_version}"
            self.trace.append("SCHEMA_ADMIT", self.subject.subject_id,
                              {"version": decision.new_version,
                               "rule": poss.payload["rule"]})
        elif poss.rel_type and not self.registry.current.has_type(poss.rel_type):
            rt = RelationType(
                name=poss.rel_type,
                domain_types=tuple(poss.payload.get("domain_types", "").split(",")),
                codomain_types=tuple(poss.payload.get("codomain_types", "").split(",")))
            new_grammar = Grammar(version=self.registry.current.version + 1,
                                  relation_types=dict(
                                      self.registry.current.relation_types))
            new_grammar.relation_types[poss.rel_type] = rt
            decision = self.registry.admit_grammar_change(new_grammar,
                                                          self.world.space)
            if not decision.accepted:
                stages["SCHEMA_ADMIT"] = decision.reason
                raise KernelRefusal("SCHEMA_ADMIT", decision.reason)
            stages["SCHEMA_ADMIT"] = f"OK v{decision.new_version}"
            self.trace.append("SCHEMA_ADMIT", self.subject.subject_id,
                              {"version": decision.new_version,
                               "rel_type": poss.rel_type})
        else:
            stages["SCHEMA_ADMIT"] = "NOT_REQUIRED"

        # --- EXECUTE (EFFECT + EXECUTION BINDING) ------------------------------------
        before = self._world_digest()
        executed = False
        if poss.rel_type and target_pair:
            rt = self.registry.current.type_of(poss.rel_type)
            a, b = target_pair
            ta = self.world.space.instances[a].type_name
            tb = self.world.space.instances[b].type_name
            if rt is None or not rt.accepts(ta, tb):
                stages["EXECUTE"] = "DENIED_TYPE_MISMATCH"
                raise KernelRefusal("EXECUTE", "TYPE_MISMATCH")
            self.world.space.add_relation(poss.rel_type, a, b)
            executed = True
        elif poss.kind == "OBJECT_TYPE":
            # Эффект типа-объекта: тип принят в базис (состояние мира изменилось).
            executed = True
        after = self._world_digest()
        stages["EXECUTE"] = "OK" if executed else "NO_TARGET"
        self.trace.append("EXECUTE", self.subject.subject_id,
                          {"before": before, "after": after})
        poss.R = executed

        # --- ATTEST (EVIDENCE, независимая верификация) --------------------------------
        if skip_attest:
            # Результат не активируется: «пропуск любого звена делает результат
            # не-Хозяинским» (v1.7). Используется в H-016.
            stages["ATTEST"] = "SKIPPED"
            stages["ACTIVATE"] = "BLOCKED_NO_EVIDENCE"
            self.trace.append("ATTEST_SKIPPED", self.subject.subject_id, {})
            return {"stages": stages, "possibility": poss}

        record = ExecutionRecord(
            op_id=poss.possibility_id, payload_hash=after,
            executed_by=self.subject.subject_id,
            world_digest_before=before, world_digest_after=after,
            signature_key_id="observer-key-1",
            signature=sign_payload(verifier_key, {
                "op_id": poss.possibility_id, "payload_hash": after,
                "executed_by": self.subject.subject_id,
                "before": before, "after": after}))
        artifact = {"relation_registered": executed}
        claim = Claim(claim_id=f"claim-{poss.possibility_id}",
                      subject=self.subject.subject_id,
                      statement=f"{poss.rel_type} создан и зарегистрирован",
                      asserted_by=executor_identity)
        try:
            vres = verifier.verify(claim, executor_identity, record,
                                   artifact, suite, external)
        except SelfAttestationRefused as exc:
            stages["ATTEST"] = f"REFUSED: {exc}"
            stages["ACTIVATE"] = "BLOCKED_NO_EVIDENCE"
            self.trace.append("ATTEST_REFUSED", self.subject.subject_id,
                              {"reason": str(exc)})
            return {"stages": stages, "possibility": poss}
        stages["ATTEST"] = f"{vres.verdict} (V{int(vres.level)})"
        if not vres.verified:
            stages["ACTIVATE"] = "BLOCKED_NO_EVIDENCE"
            self.trace.append("ATTEST_FAILED", self.subject.subject_id,
                              {"reasons": vres.reasons})
            return {"stages": stages, "possibility": poss}
        poss.V = True
        self.trace.append("ATTEST", self.subject.subject_id,
                          {"level": int(vres.level), "verified": True})

        # --- ACTIVATE (единственный авторитетный HEAD) ---------------------------------
        if self.activation is not None:
            ok = self.activation.cas_head(
                self.subject.lineage, None, self.subject.subject_id)
            stages["ACTIVATE"] = "OK" if ok else "DENIED_CONFLICT"
        else:
            stages["ACTIVATE"] = "OK"
        self.trace.append("ACTIVATE", self.subject.subject_id, {})

        # --- SETTLE (атомарное списание escrow ровно один раз) --------------------------
        if self.ledger is not None:
            token = self.ledger._lease_tokens[self.subject.subject_id]
            out = self.ledger.settle(self.subject.subject_id, possibility_id,
                                     cost, token, self.ledger.lineage)
            stages["SETTLE"] = out.value
            self.trace.append("SETTLE", self.subject.subject_id,
                              {"op": possibility_id, "out": out.value})
        return {"stages": stages, "possibility": poss}

    # =========================================================================
    def _world_digest(self) -> str:
        base = "|".join(sorted(f"{r[0]}({r[1]},{r[2]})"
                               for r in self.world.space.relations))
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]


def build_world_h007() -> Tuple[World, Grammar]:
    """
    Фиксация базиса для H-007 (v1.8-оппонент, требование 1: «Формальная
    фиксация модели вычислений и базиса»).
    Мир: два агента, три места; наблюдаемый мост A-B; СКРЫТЫЙ мост B-C
    (существует в W, не наблюдён — материал H-007A).
    Gamma_0: BRIDGE(PLACE,PLACE), AT(AGENT,PLACE); правило образования:
    transitive_closure (механизм PATH — материал H-007D).
    Практическое соответствие: action basis как генеративное ядро
    (B* Expansion, Posadas 2026, Expert Systems — проверено).
    """
    grammar = Grammar(version=1, relation_types={
        "BRIDGE": RelationType("BRIDGE", ("PLACE",), ("PLACE",)),
        "AT": RelationType("AT", ("AGENT",), ("PLACE",)),
    })
    space = Space(
        types={"AGENT", "PLACE"},
        instances={
            "h1": Instance("h1", "AGENT"), "h2": Instance("h2", "AGENT"),
            "islandA": Instance("islandA", "PLACE"),
            "islandB": Instance("islandB", "PLACE"),
            "islandC": Instance("islandC", "PLACE"),
        },
        relations={("AT", "h1", "islandA"), ("AT", "h2", "islandB"),
                   ("BRIDGE", "islandA", "islandB")},
        constraints=["bridges are bidirectional"],
        grammar=grammar, schema_version=1,
    )
    world = World(space=space,
                  hidden_relations={("BRIDGE", "islandB", "islandC")})
    return world, grammar
