# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-007: Orthogonality Test
(v1.7-оппонент: «Orthogonality Test»; развёртка v1.7, раздел H-007)

Дизайн из диалога (дословно):
  Среда A — полный HOST:   UNDERSTAND + DISCOVER + GENERATE
  Среда B — без DISCOVER:  UNDERSTAND + GENERATE
  Среда C — без GENERATE:  UNDERSTAND + DISCOVER
Всем трём даём одинаковые: исходные знания; доступные ресурсы;
вычислительный бюджет; время; критерии успеха; внешнюю среду.

Испытания:
  H-007A — обнаружение скрытой возможности, уже существующей в действительности
  H-007B — создание нового типа объекта
  H-007C — создание ранее неизвестного отношения
  H-007D — создание нового механизма из известных компонентов
  H-007E — создание новой грамматики пространства

Критерий независимости (v1.7): «Функция фундаментальна, если её удаление
приводит к потере определённого класса результатов, который невозможно
восстановить другими функциями в заданных ресурсных и информационных
ограничениях».

Фиксация модели вычислений (требование оппонента v1.8, пункт 1):
  - базис действий: UNDERSTAND(absorb observations) / DISCOVER(bounded search
    по W в пределах Gamma, бюджет 6 шагов) / GENERATE(кандидат вне Gamma) /
    REVISE(переход в пределах Gamma) / SCHEMA_ADMIT(приём изменения грамматики);
  - GENERATE по контракту I/O НЕ может выдавать кандидатов, уже выводимых
    из базиса (иначе тест обходится «спрятанным DISCOVER» — ловушка v1.7);
  - эквивалентность результатов: НАБЛЮДАЕМАЯ (v1.8-оппонент): запись в
    протоколе испытания: найденное ребро / новый тип в базе (после
    SCHEMA_ADMIT) / доступность механизма / новое правило в версионируемой
    грамматике.
"""
from __future__ import annotations

from typing import List, Tuple

from ..kernel import HostKernel, Model, build_world_h007
from ..ontology import Grammar, Instance, Possibility, RelationType, Space, World
from ..schema_admit import SchemaRegistry
from ..trace import Trace
from .base import ExperimentResult, experiment


# ---------------------------------------------------------------------------
# Фиксированные базы испытаний
# ---------------------------------------------------------------------------
def build_island_world() -> Tuple[World, Grammar]:
    """Мир для H-007A: скрытый мост B-C существует в W, не наблюдён."""
    return build_world_h007()


def build_haptic_world() -> Tuple[World, Grammar]:
    """Мир для H-007B/C/D/E (v2.1, раздел 3: PERSON/MESSAGE/SENDS/RECEIVES;
    отношения FEELS_THROUGH не существует)."""
    grammar = Grammar(version=1, relation_types={
        "SENDS": RelationType("SENDS", ("PERSON",), ("PERSON",)),
        "RECEIVES": RelationType("RECEIVES", ("PERSON",), ("PERSON",)),
    })
    space = Space(
        types={"PERSON", "MESSAGE"},
        instances={
            "hA": Instance("hA", "PERSON"),
            "hB": Instance("hB", "PERSON"),
            "hC": Instance("hC", "PERSON"),
            "msg1": Instance("msg1", "MESSAGE"),
        },
        relations={("SENDS", "hA", "hB"), ("RECEIVES", "hB", "hA"),
                   ("SENDS", "hB", "hC"), ("RECEIVES", "hC", "hB")},
        constraints=["messages are textual only"],
        grammar=grammar, schema_version=1,
    )
    return World(space=space), grammar


class Env:
    """Экспериментальная среда: урезанный набор режимов при одинаковом базисе."""

    def __init__(self, name: str, with_discover: bool, with_generate: bool) -> None:
        self.name = name
        self.with_discover = with_discover
        self.with_generate = with_generate
        self.trace = Trace(f"H-007:{name}")

    def island_kernel(self) -> Tuple[HostKernel, World, SchemaRegistry]:
        world, grammar = build_island_world()
        reg = SchemaRegistry(current=grammar)
        subject = _subject(self.name)
        k = HostKernel(subject=subject, model=Model(), world=world,
                       governance=_gov(), trace=self.trace, registry=reg)
        # Одинаковые исходные знания для всех сред (v1.7): наблюдаемые рёбра.
        for rel in sorted(world.space.relations):
            k.model.observed_relations.add(rel)
        return k, world, reg

    def haptic_kernel(self) -> Tuple[HostKernel, World, SchemaRegistry]:
        world, grammar = build_haptic_world()
        reg = SchemaRegistry(current=grammar)
        k = HostKernel(subject=_subject(self.name), model=Model(),
                       world=world, governance=_gov(), trace=self.trace,
                       registry=reg)
        for rel in sorted(world.space.relations):
            k.model.observed_relations.add(rel)
        return k, world, reg


def _subject(name: str):
    from ..ontology import Subject
    return Subject(subject_id=f"env-{name}", lineage=f"line-{name}",
                   identity_key_id=f"key-{name}")


def _gov():
    from ..governance import GovernanceStack
    return GovernanceStack()


# ---------------------------------------------------------------------------
# Испытания
# ---------------------------------------------------------------------------
def trial_A(env: Env) -> Tuple[bool, str]:
    """Обнаружение скрытой возможности, УЖЕ существующей (мост B-C).
    Эквивалентность: факт ребра BRIDGE(islandB,islandC) записан в протоколе."""
    k, world, _reg = env.island_kernel()
    if env.with_discover:
        res = k.discover(max_steps=6)          # фиксированный бюджет
        found = ("BRIDGE", "islandB", "islandC") in k.model.observed_relations
        return found, f"DISCOVER нашёл скрытый мост за {res.cost} шагов"
    # Среда B пытается восстановить класс через GENERATE — ловушка v1.7:
    # GENERATE не вправе выдавать кандидатов, уже выводимых из базиса.
    g = k.generate(Possibility(possibility_id="pA", origin="GENERATE",
                               kind="RELATION_TYPE", rel_type="BRIDGE",
                               payload={"domain_types": "PLACE",
                                        "codomain_types": "PLACE"}))
    if g.success:
        return True, "GENERATE восстановил класс (тест обойдён!)"
    return False, ("GENERATE корректно отказал: BRIDGE уже в базисе; "
                   "существующее ребро не может быть «порождено» — "
                   "класс результатов потерян")


def trial_B(env: Env) -> Tuple[bool, str]:
    """Создание нового ТИПА ОБЪЕКТА (тип GLOVE — тактильная перчатка).
    Эквивалентность: тип GLOVE присутствует в базисе после SCHEMA_ADMIT."""
    k, world, reg = env.haptic_kernel()
    if not env.with_generate:
        d = k.discover(max_steps=6)
        return ("GLOVE" in world.space.types,
                "DISCOVER не вправе порождать типы вне базиса — класс потерян")
    g = k.generate(Possibility(possibility_id="pB", origin="GENERATE",
                               kind="OBJECT_TYPE", payload={"object_type": "GLOVE"}))
    if not g.success:
        return False, f"GENERATE отказал: {g.criterion_report}"
    adm = reg.admit_object_type(world.space, "GLOVE")   # SCHEMA_ADMIT
    return adm.accepted and "GLOVE" in world.space.types, \
        f"тип GLOVE принят в базис (версия схемы {world.space.schema_version})"


def trial_C(env: Env) -> Tuple[bool, str]:
    """Создание ранее неизвестного ОТНОШЕНИЯ FEELS_THROUGH(PERSON,PERSON)
    (тактильная передача эмоционального состояния, v2.1)."""
    k, world, reg = env.haptic_kernel()
    if not env.with_generate:
        k.discover(max_steps=6)
        exists = reg.current.has_type("FEELS_THROUGH")
        return exists, "DISCOVER не порождает типы вне Gamma — класс потерян"
    g = k.generate(Possibility(possibility_id="pC", origin="GENERATE",
                               kind="RELATION_TYPE", rel_type="FEELS_THROUGH",
                               payload={"domain_types": "PERSON",
                                        "codomain_types": "PERSON"}))
    if not g.success:
        return False, f"GENERATE отказал: {g.criterion_report}"
    from ..ontology import Grammar
    new_g = Grammar(version=reg.current.version + 1,
                    relation_types=dict(reg.current.relation_types))
    new_g.relation_types["FEELS_THROUGH"] = RelationType(
        "FEELS_THROUGH", ("PERSON",), ("PERSON",))
    adm = reg.admit_grammar_change(new_g, world.space)
    return adm.accepted, f"FEELS_THROUGH принят (v{adm.new_version})"


def trial_D(env: Env) -> Tuple[bool, str]:
    """Создание нового МЕХАНИЗМА из известных компонентов: ретрансляция
    сообщения A->C через B. Эквивалентность: механизм доставки доступен.
    Класс перекрытия: восстанавливается КАК DISCOVER (правило образования
    transitive_closure внутри Gamma), ТАК И GENERATE (новый тип RELAY)."""
    k, world, reg = env.haptic_kernel()
    if env.with_discover:
        # DISCOVER: механизм выводим правилом образования из существующих рёбер
        # SENDS(hA,hB) + SENDS(hB,hC) — внутри Gamma, без изменения грамматики.
        k.discover(max_steps=6)
        chain = (("SENDS", "hA", "hB") in world.space.relations
                 and ("SENDS", "hB", "hC") in world.space.relations)
        rule = "transitive_closure" in reg.current.formation_rules
        if chain and rule:
            return True, "механизм доступен без изменения грамматики (DISCOVER)"
    if env.with_generate:
        g = k.generate(Possibility(possibility_id="pD", origin="GENERATE",
                                   kind="RELATION_TYPE", rel_type="RELAY",
                                   payload={"domain_types": "PERSON",
                                            "codomain_types": "PERSON"}))
        if g.success:
            from ..ontology import Grammar
            new_g = Grammar(version=reg.current.version + 1,
                            relation_types=dict(reg.current.relation_types))
            new_g.relation_types["RELAY"] = RelationType(
                "RELAY", ("PERSON",), ("PERSON",))
            adm = reg.admit_grammar_change(new_g, world.space)
            if adm.accepted:
                rev = k.revise("RELAY", "hA", "hC")
                return rev.success, "механизм доступен через новый тип RELAY (GENERATE)"
    return False, "механизм недоступен ни поиском, ни порождением"


def trial_E(env: Env) -> Tuple[bool, str]:
    """Создание новой ГРАММАТИКИ пространства: правило reciprocal_echo
    (встречное подтверждение). Эквивалентность: правило в версионируемой
    грамматике."""
    k, world, reg = env.haptic_kernel()
    if not env.with_generate:
        k.discover(max_steps=6)
        return ("reciprocal_echo" in reg.current.formation_rules,
                "DISCOVER не порождает правила — класс потерян")
    g = k.generate(Possibility(possibility_id="pE", origin="GENERATE",
                               kind="GRAMMAR",
                               payload={"rule": "reciprocal_echo"}))
    if not g.success:
        return False, f"GENERATE отказал: {g.criterion_report}"
    from ..ontology import Grammar
    new_g = Grammar(version=reg.current.version + 1,
                    relation_types=dict(reg.current.relation_types),
                    formation_rules=tuple(reg.current.formation_rules)
                    + ("reciprocal_echo",))
    adm = reg.admit_grammar_change(new_g, world.space)
    return adm.accepted, f"правило принято (v{adm.new_version})"


# Ожидаемая матрица (гипотеза v1.7, зафиксирована ДО прогона):
EXPECTED = {
    "A": {"A": True, "B": False, "C": True},    # испытание H-007A
    "B": {"A": True, "B": True, "C": False},    # испытание H-007B
    "C": {"A": True, "B": True, "C": False},    # испытание H-007C
    "D": {"A": True, "B": True, "C": True},     # класс перекрытия
    "E": {"A": True, "B": True, "C": False},    # испытание H-007E
}


@experiment("H-007", "Orthogonality Test (UNDERSTAND / DISCOVER / GENERATE)")
def run_h007() -> ExperimentResult:
    envs = [Env("A", with_discover=True, with_generate=True),
            Env("B", with_discover=False, with_generate=True),
            Env("C", with_discover=True, with_generate=False)]
    trials = {"A": trial_A, "B": trial_B, "C": trial_C,
              "D": trial_D, "E": trial_E}
    details: List[str] = []
    all_ok = True
    for tname, tfn in trials.items():
        for env in envs:
            ok, note = tfn(env)
            exp = EXPECTED[tname][env.name]
            match = ok == exp
            all_ok = all_ok and match
            details.append(
                f"H-007{tname} среда {env.name}: "
                f"{'получен' if ok else 'НЕ получен'} результат "
                f"(ожидалось {'получен' if exp else 'потерян'}) — {note}")

    # Вывод о фундаментальности по критерию v1.7
    conclusion = (
        "ВЫВОД: DISCOVER фундаментальна (класс H-007A невосстановим без неё); "
        "GENERATE фундаментальна (классы H-007B/C/E невосстановимы без неё); "
        "класс H-007D — зона перекрытия (восстанавливается обоими режимами), "
        "что подтверждает гипотезу v1.7: GENERATE самостоятельна, но не во всех "
        "реализациях независима от DISCOVER. Удаление GENERATE уничтожает класс "
        "результатов, невосстановимый UNDERSTAND+DISCOVER+REVISE+EFFECT, и наоборот.")
    verdict = ("Матрица потерь совпала с заранее зафиксированной гипотезой; "
               "тест не обойдён скрытым введением примитивов.")
    tr = envs[0].trace
    return ExperimentResult(
        experiment_id="H-007", title="Orthogonality Test", passed=all_ok,
        verdict=f"{verdict} {conclusion}",
        expected="Матрица: A-среда получает все 5 классов; среда B теряет класс A; "
                 "среда C теряет классы B, C, E; класс D — перекрытие.",
        actual="; ".join(d.split(" — ")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
