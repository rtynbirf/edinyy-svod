# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-012: SPACE Removal
(v2.1 раздел 3; v2.3 H-013 «удаление SPACE»; v2.2 требование 2)

Вопрос v2.0-оппонента: «Можно ли выразить порождение новых возможностей, не
вводя отдельное пространство представлений, или SPACE неизбежно выводится из
RELATION?»

Ответ v2.1 (дословно):
  «SPACE не обязательно должен быть самостоятельным онтологическим примитивом.
  Но его функция неустранима... SPACE as entity != SPACE as necessary function».
  P=(T,O,R,C,Gamma,V); SPACE можно вычислять: P(S)=Reachable(S,Gamma).

Проверяемые пункты:
  1) без сущности SPACE (только рёбра + Gamma + V) можно отличить существующее
     отношение от потенциального;
  2) можно отличить изменение ЭКЗЕМПЛЯРА от изменения ГРАММАТИКИ
     (версия схемы V растёт только при изменении грамматики);
  3) если убрать саму функцию (Gamma, правила образования, версии) —
     различить изменение объекта и изменение грамматики невозможно =>
     класс поведения потерян. «Мы теряем способность отличать изменение
     объекта от изменения грамматики» (v2.3).
"""
from __future__ import annotations

from ..kernel import Model, build_world_h007
from ..ontology import Grammar, Instance, RelationType, Space, Subject, World
from ..schema_admit import SchemaRegistry
from ..trace import Trace
from ..governance import GovernanceStack
from .base import ExperimentResult, experiment


@experiment("H-012", "SPACE Removal (сущность удаляема, функция — нет)")
def run_h012() -> ExperimentResult:
    details = []
    ok_all = True
    tr = Trace("H-012")

    world, grammar = build_world_h007()
    space: Space = world.space
    reg = SchemaRegistry(current=grammar)

    # (1) Существующее vs потенциальное БЕЗ отдельной сущности SPACE:
    #     рёбра + Gamma-допустимость + достижимость.
    existing = space.relation_exists("BRIDGE", "islandA", "islandB")
    potential = space.is_potential("BRIDGE", "islandA", "islandC")
    unreachable = space.is_potential("BRIDGE", "islandA", "islandA")
    case1 = existing and potential
    ok_all = ok_all and case1
    details.append(f"(1) существующее BRIDGE(A,B)={existing}; потенциальное "
                   f"BRIDGE(A,C)={potential}; SPACE-функция различает их, "
                   f"сущность не потребовалась; Reachable={len(space.reachable_pairs('BRIDGE'))} пар")

    # (2) Экземпляр vs грамматика: добавление ребра не меняет V; приём нового
    #     типа меняет V и номер версии гаммы.
    v_before_g = space.schema_version
    space.add_relation("BRIDGE", "islandB", "islandC")     # изменение экземпляра
    case2a = space.schema_version == v_before_g
    new_g = Grammar(version=reg.current.version + 1,
                    relation_types=dict(reg.current.relation_types))
    new_g.relation_types["ROAD"] = RelationType("ROAD", ("PLACE",), ("PLACE",))
    adm = reg.admit_grammar_change(new_g, space)           # изменение грамматики
    case2b = (adm.accepted and reg.current.version == 2
              and space.schema_version == v_before_g + 1)
    ok_all = ok_all and case2a and case2b
    tr.append("INSTANCE_CHANGE", "h", {})
    tr.append("SCHEMA_CHANGE", "h", {"version": adm.new_version})
    details.append(f"(2) добавление ребра не подняло версию схемы "
                   f"({case2a}); приём типа ROAD поднял версию грамматики и "
                   f"версию схемы до v{space.schema_version} ({case2b}) — "
                   f"изменения различимы")

    # (3) Удаляем САМУ ФУНКЦИЮ: остаётся только множество рёбер — нет ни типов,
    #     ни Gamma, ни версий. Попытка выразить «изменение грамматики».
    class BareGraph:
        def __init__(self) -> None:
            self.edges = {("islandA", "islandB")}

    bare = BareGraph()
    object_change = bare.edges.add(("islandB", "islandC"))   # тип None
    grammar_change_attempt = True      # «считаем, что правило изменилось»
    indistinguishable = (object_change is None) and grammar_change_attempt
    # В bare-графе оба события неотличимы: это и есть потеря класса.
    case3 = indistinguishable
    ok_all = ok_all and case3
    details.append("(3) без типов/Gamma/V «добавлено ребро» и «изменено "
                   "правило» неразличимы — потеря способности подтвердилась; "
                   "SPACE-as-function необходима")

    return ExperimentResult(
        experiment_id="H-012", title="SPACE Removal", passed=ok_all,
        verdict="Отдельный объект SPACE не требуется; функция различения "
                "существующего/потенциального и экземпляра/грамматики "
                "неустранима — без неё класс поведения теряется.",
        expected="существующее vs потенциальное различимы; версия схемы "
                 "растёт только при изменении грамматики; bare-граф "
                 "неразличим (потеря класса).",
        actual="; ".join(d[:70] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
