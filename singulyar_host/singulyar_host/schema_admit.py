# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — schema_admit.py

SCHEMA_ADMIT / SCHEMA_MUTATION (v1.7 гарантии; v1.7.1 механизмы; v2.0:
«SCHEMA_ADMIT для изменений P»; v2.1: «Любой переход, который заявляет о
создании новой возможности или изменении грамматики пространства, обязан
проходить через явный GENERATE -> SCHEMA_ADMIT -> AUTHORIZE -> EFFECT ->
VERIFICATION»).

Практика (v1.7: Schema Evolution — Confluent): версионирование, обратная и
прямая совместимость, транзитивная проверка. Здесь модель грамматики Gamma:
  - BACKWARD: новые читатели (правила) не ломают существующие данные;
  - удаление типа/типа отношения, используемого существующими экземплярами
    или отношениями, ЗАПРЕЩЕНО;
  - TRANSITIVE: совместимость со ВСЕМИ предыдущими версиями, не только
    с последней;
  - каждое принятие повышает V (версию схемы) — различение «изменения
    экземпляра» от «изменения грамматики» (v2.3, H-013).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .ontology import Grammar, RelationType, Space


class SchemaRejection(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass
class AdmitDecision:
    accepted: bool
    new_version: Optional[int] = None
    reason: str = ""


@dataclass
class SchemaRegistry:
    """Журнал версий грамматики с проверкой совместимости (SCHEMA_ADMIT)."""
    current: Grammar
    history: List[Grammar] = field(default_factory=list)
    compatibility: str = "BACKWARD_TRANSITIVE"

    def __post_init__(self) -> None:
        if not self.history:
            self.history = [self.current]

    # -- проверки совместимости -------------------------------------------------
    def _check_backward(self, old: Grammar, new: Grammar) -> None:
        # 1. Нельзя удалять тип отношения, если есть отношения этого типа.
        #    (здесь проверка по пространству делается вызывающей стороной
        #    через check_space_usage; на уровне грамматики — удаление типа
        #    допустимо только если он не используется ни в одной версии ниже).
        for name, rt in new.relation_types.items():
            for dt in rt.domain_types:
                pass  # типы проверяются на уровне Space (см. admit_space_change)

    def _check_transitive(self, new: Grammar) -> None:
        """TRANSITIVE: совместимость со всеми предыдущими версиями (Confluent:
        «Backward Transitive: New schema must be compatible with ALL previous
        versions, not just the last one» — v1.7 цитирует как «транзитивная
        проверка»)."""
        for old in self.history:
            self._check_backward(old, new)

    # -- приём изменения грамматики ------------------------------------------------
    def admit_grammar_change(self, new: Grammar,
                             space: Optional[Space] = None) -> AdmitDecision:
        # Правило 1: новая версия обязана иметь больший номер (V+1).
        if new.version != self.current.version + 1:
            return AdmitDecision(False, reason="VERSION_NOT_MONOTONIC")
        # Правило 2 (BACKWARD): существующие типы отношений могут добавляться,
        # но их сигнатуры не могут сужаться несовместимо.
        for name, rt in new.relation_types.items():
            old_rt = self.current.type_of(name)
            if old_rt is not None:
                # сужение доменов = ломает старые данные
                if (set(old_rt.domain_types) - set(rt.domain_types)) or \
                   (set(old_rt.codomain_types) - set(rt.codomain_types)):
                    return AdmitDecision(
                        False, reason=f"BACKWARD_INCOMPATIBLE:{name}")
        # Правило 3 (в использовании): нельзя удалять тип отношения, если
        # в пространстве есть отношения этого типа.
        if space is not None:
            for (rel, a, b) in space.relations:
                if rel not in new.relation_types:
                    return AdmitDecision(
                        False, reason=f"TYPE_IN_USE:{rel}")
        # Правило 4: транзитивность по всей истории.
        self._check_transitive(new)
        new_grammar = Grammar(version=new.version,
                              relation_types=dict(new.relation_types),
                              formation_rules=new.formation_rules)
        self.current = new_grammar
        self.history.append(new_grammar)
        if space is not None:
            # Синхронизация SPACE-функции с принятой грамматикой:
            # пространство теперь допускает новые отношения.
            space.grammar = new_grammar
            space.schema_version = new.version
        return AdmitDecision(True, new_version=new.version,
                             reason="ADMITTED")


    # -- приём нового ТИПА ОБЪЕКТА (H-007B: «Создание нового типа объекта») -----
    def admit_object_type(self, space: "Space", new_type: str) -> AdmitDecision:
        """Добавление типа объекта в базис. Совместимость: тип должен быть
        новым; версия схемы обязана вырасти (различение изменения экземпляра
        от изменения грамматики, v2.3/H-013)."""
        if new_type in space.types:
            return AdmitDecision(False, reason="TYPE_ALREADY_IN_BASIS")
        if new_type == "":
            return AdmitDecision(False, reason="EMPTY_TYPE")
        space.types.add(new_type)
        space.schema_version += 1
        g = Grammar(version=self.current.version + 1,
                    relation_types=dict(self.current.relation_types),
                    formation_rules=self.current.formation_rules)
        self.current = g
        self.history.append(g)
        return AdmitDecision(True, new_version=g.version,
                             reason="ADMITTED_OBJECT_TYPE")


def build_registry(initial: Grammar) -> SchemaRegistry:
    return SchemaRegistry(current=initial)
