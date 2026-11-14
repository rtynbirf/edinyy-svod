# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — ontology.py

Онтологическое основание, собранное из всех реплик диалога (v1.6 -> v2.3):

  SUBJECT      — различимый носитель с историей, обязательствами и границами
                 (v2.2/v2.3). Идентичность не равна учётным данным (NIST tenet 1,
                 цит. в v1.9/v2.1/v2.2).
  DOMAIN D_i   — домен суверенного управления: D_i=(S_i, R_i, C_i, A_i) (v2.1,
                 раздел 4 «NON-APPROPRIATION»).
  SPACE        — НЕ обязательная сущность, но НЕОБХОДИМАЯ функция (v2.1 раздел 3,
                 v2.3 раздел 6/H-013): P=(T,O,R,C,Gamma,V) — типы, экземпляры,
                 отношения, ограничения, правила образования, версия схемы.
                 SPACE-as-entity != SPACE-as-necessary-function.
  GRAMMAR      — правила образования допустимых отношений Gamma (v2.1: раздел 3).
  TRANSITION   — изменение состояния, отношений и пространства возможностей
                 (v2.0/v2.1/v2.2/v2.3).
  POSSIBILITY  — объект возможности с НЕЗАВИСИМЫМИ координатами
                 Q=(E,D,A,R,V) (реплика оппонента v1.7: «Линейный жизненный
                 цикл PossibilityObject слишком груб. Независимые координаты
                 Q=(E,D,A,R,V) лучше описывают реальные состояния»).
                 E — экземпляр существует в модели; D — обнаружен;
                 A — авторизован; R — реализован; V — верифицирован.
  COMMITMENT   — обязательство как объект (v1.7.1: список объектов C).
  WORLD        — действительность W, в том числе «скрытые» отношения, которые
                 существуют, но не наблюдались (материал для DISCOVER, v1.7
                 испытание H-007A).

Ключевые различения диалога, зафиксированные здесь кодом:
  DISCOVER != GENERATE != REALIZE   (v1.9, раздел 4)
  STATE != HISTORY != EVENT         (v1.9, раздел 1.B) — см. trace.py
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Вердикты проверок. (v2.1, Continuity Vector: «результаты могут быть
# PASS, FAIL, UNKNOWN, CONTESTED» + добавлен REFUSED для корректных отказов;
# v2.1, матрица H-010..H-016: «Корректный отказ тоже может быть успешным
# результатом теста».)
# ---------------------------------------------------------------------------
class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    CONTESTED = "CONTESTED"
    REFUSED = "REFUSED"


# ---------------------------------------------------------------------------
# COMMITMENT — обязательство (v1.7.1: объекты; v2.1: «O — Obligations»)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Commitment:
    commitment_id: str
    holder: str                 # субъект, несущий обязательство
    claim: str                  # текст обязательства
    binding_on_successors: bool = True   # переносится ли на преемников


# ---------------------------------------------------------------------------
# DOMAIN — домен суверенного управления D_i=(S_i, R_i, C_i, A_i) (v2.1, разд. 4)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Domain:
    subject_id: str                              # S_i — собственная область
    relations_in_scope: FrozenSet[str]           # R_i — связи в пределах домена
    commitments: FrozenSet[Commitment]           # C_i — обязательства
    authorities_in_scope: FrozenSet[str]         # A_i — полномочия в домене
    # EXIT_j ∉ A_i — право выхода другого субъекта никогда не входит в чужой
    # домен (v2.1: «субъект A не может присвоить себе полномочие отменить
    # право выхода субъекта B»). Проверяется функцией is_exit_inside().
    exit_right_of_others: FrozenSet[str] = frozenset()

    def is_exit_inside(self, other_subject: str) -> bool:
        return other_subject in self.exit_right_of_others


# ---------------------------------------------------------------------------
# SPACE как функция: P=(T, O, R, C, Gamma, V)
# (v2.1 разд. 3: типы, экземпляры, отношения, ограничения, правила, версия)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RelationType:
    """Тип отношения в грамматике Gamma: имя + типы домена/кодомена."""
    name: str
    domain_types: Tuple[str, ...]     # допустимые типы субъекта отношения
    codomain_types: Tuple[str, ...]   # допустимые типы объекта отношения

    def accepts(self, dom_type: str, cod_type: str) -> bool:
        return dom_type in self.domain_types and cod_type in self.codomain_types


@dataclass
class Grammar:
    """
    Gamma — правила образования допустимых отношений (v2.1 разд. 3: «(Gamma) —
    правила образования допустимых отношений»; v2.3 H-014: Gamma_0={parent,
    owns,delegates} -> Gamma_1=Gamma_0 ∪ {co_creates}).
    """
    version: int
    relation_types: Dict[str, RelationType]
    # Правило образования «PATH»: транзитивное замыкание существующих рёбер
    # (класс D испытания H-007D — «новый механизм из известных компонентов»).
    formation_rules: Tuple[str, ...] = ("transitive_closure",)

    def has_type(self, name: str) -> bool:
        return name in self.relation_types

    def type_of(self, name: str) -> Optional[RelationType]:
        return self.relation_types.get(name)

    def copy_with_version(self, version: int) -> "Grammar":
        return Grammar(version=version,
                       relation_types=dict(self.relation_types),
                       formation_rules=self.formation_rules)


@dataclass
class Instance:
    """Экземпляр объекта в пространстве: (O) — экземпляры."""
    instance_id: str
    type_name: str
    properties: Dict[str, str] = field(default_factory=dict)


@dataclass
class Space:
    """
    SPACE-as-function. Реализует P=(T,O,R,C,Gamma,V):
      T — типы; O — экземпляры; R — существующие отношения;
      C — ограничения; Gamma — правила образования; V — версия схемы.
    Порождаемые возможности = то, что допустимо грамматикой, но ещё не
    существует (v2.3: «P(S)=Reachable(S,Gamma)»; «Нельзя просто удалить
    различие между существующим и потенциально возможным»).
    """
    types: Set[str]
    instances: Dict[str, Instance]
    relations: Set[Tuple[str, str, str]]          # (rel_type, from_id, to_id)
    constraints: List[str]
    grammar: Grammar
    schema_version: int

    # -- существующее vs потенциальное (ядро функции SPACE) -------------------
    def relation_exists(self, rel_type: str, a: str, b: str) -> bool:
        return (rel_type, a, b) in self.relations

    def relation_type_admissible(self, rel_type: str, a: str, b: str) -> bool:
        """Потенциальная возможность: тип в Gamma, типы сторон подходят,
        но отношение ещё не существует."""
        rt = self.grammar.type_of(rel_type)
        if rt is None:
            return False
        ta = self.instances[a].type_name if a in self.instances else None
        tb = self.instances[b].type_name if b in self.instances else None
        return rt.accepts(ta, tb)

    def is_potential(self, rel_type: str, a: str, b: str) -> bool:
        return (not self.relation_exists(rel_type, a, b)
                and self.relation_type_admissible(rel_type, a, b))

    def reachable_pairs(self, rel_type: str) -> List[Tuple[str, str]]:
        """Reachable(S, Gamma) для заданного типа отношения (v2.3, H-013)."""
        out = []
        ids = list(self.instances)
        for a, b in itertools.product(ids, ids):
            if self.is_potential(rel_type, a, b):
                out.append((a, b))
        return out

    def add_relation(self, rel_type: str, a: str, b: str) -> None:
        self.relations.add((rel_type, a, b))

    def copy(self) -> "Space":
        return Space(
            types=set(self.types),
            instances=dict(self.instances),
            relations=set(self.relations),
            constraints=list(self.constraints),
            grammar=self.grammar.copy_with_version(self.grammar.version),
            schema_version=self.schema_version,
        )


# ---------------------------------------------------------------------------
# WORLD — действительность (W оператора H из v1.9: (S,W,P,E,C) -> (S',W',P',O)).
# Может содержать скрытые факты, которых нет в модели субъекта.
# ---------------------------------------------------------------------------
@dataclass
class World:
    space: Space
    # Скрытые (реально существующие, но ещё не наблюдённые) отношения.
    hidden_relations: Set[Tuple[str, str, str]] = field(default_factory=set)

    def reveal(self, rel_type: str, a: str, b: str) -> bool:
        """Наблюдение скрытого отношения: факт переходит из W в свидетельство."""
        if (rel_type, a, b) in self.hidden_relations:
            self.hidden_relations.remove((rel_type, a, b))
            self.space.add_relation(rel_type, a, b)
            return True
        return False


# ---------------------------------------------------------------------------
# SUBJECT — различимый носитель (v2.2/v2.3)
# ---------------------------------------------------------------------------
@dataclass
class Subject:
    subject_id: str
    lineage: str                                   # L — происхождение/линия
    epoch: int = 0                                 # привязка к эпохе (H-009)
    substrate: str = "python-process"              # субстрат (H-011)
    identity_key_id: str = ""                      # IDENTITY != CREDENTIAL (v2.3)
    model_id: str = "model-A"                      # для испытания H-008
    weights_hash: str = "w-default"
    domain: Optional[Domain] = None
    commitments: Tuple[Commitment, ...] = ()
    retired: bool = False                          # старый экземпляр при переносе
    status: str = "ACTIVE"                         # ACTIVE/AUTHORITATIVE/FORKED/...
    state_hash: str = ""                           # хеш состояния (для H-010)

    def copy_for_fork(self, new_id: str) -> "Subject":
        """Клон с одинаковой памятью, историей, предпочтениями, полномочиями и
        идентификатором исходного субъекта (v2.3, H-010: S_A=clone(S_0))."""
        c = Subject(
            subject_id=new_id,
            lineage=self.lineage,          # тот же lineage — в этом и ловушка
            epoch=self.epoch,
            substrate=self.substrate,
            identity_key_id=self.identity_key_id,   # скопированный ключ!
            model_id=self.model_id,
            weights_hash=self.weights_hash,
            domain=self.domain,
            commitments=self.commitments,
            state_hash=self.state_hash,
        )
        c.status = "CLONE_PENDING"
        return c


# ---------------------------------------------------------------------------
# POSSIBILITY и координаты Q=(E,D,A,R,V)
# ---------------------------------------------------------------------------
@dataclass
class Possibility:
    """Кандидат возможности: новый тип/отношение/механизм (GENERATE) либо
    существующая, но не реализованная возможность (DISCOVER)."""
    possibility_id: str
    origin: str                      # "DISCOVER" или "GENERATE"
    kind: str                        # "INSTANCE" | "RELATION_TYPE" | "GRAMMAR"
    rel_type: Optional[str] = None
    payload: Dict[str, str] = field(default_factory=dict)
    # Q-координаты (v1.7-оппонент): независимые, не линейный жизненный цикл.
    E: bool = False   # Exists-in-model: экземпляр/тип представлен в модели
    D: bool = False   # Discovered: выявлен как существующий/достижимый
    A: bool = False   # Authorized: полномочие и допуск получены
    R: bool = False   # Realized: реализован в действительности
    V: bool = False   # Verified: независимо подтверждён (V3)

    def as_dict(self) -> Dict[str, bool]:
        return {"E": self.E, "D": self.D, "A": self.A, "R": self.R, "V": self.V}
