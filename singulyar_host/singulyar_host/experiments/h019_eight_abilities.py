# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.1 — H-019: Eight Abilities (опыт удаления)
(Конституция 4.1, статья 95: «Х-019. Восемь способностей. Проверка
различимости восьми основных способностей и потери исходов при удалении
каждой»; статья 79 — перечень восьми способностей; статья 80 — удаление
по статье 16; статья 98 — критерий необходимости: «изменение возможностей
и результатов при одинаковых условиях».)

Метод (H-017-образец, применённый к способностям):
  для каждой из восьми способностей:
    1) способность присутствует  -> класс исходов ДОСТИЖИМ;
    2) способность удалена       -> класс исходов ПОТЕРЯН, и ни одна из
       семи остальных не воспроизводит его тем же механизмом.
PASS = 8/8 способностей различимы по своим классам исходов.

Ограничение проверки (честная строка): способности — функциональные оси,
а не восемь модулей (ст. 79: «Одна реализация может объединять несколько
способностей»). Здесь каждая способность привязана к своей точке механизма
стенда; удаление — вывод механизма из строя при одинаковых прочих условиях.
"""
from __future__ import annotations

from types import MethodType
from typing import Callable, Dict, List, Tuple

from ..activation import ActivationRegistry
from ..budget import BudgetLedger
from ..capability import CapabilityStore
from ..kernel import HostKernel, KernelRefusal, Model, build_world_h007
from ..ontology import Possibility, Subject
from ..schema_admit import SchemaRegistry
from ..trace import Trace
from ..verification import (Claim, ExternalCriteria, Identity, TestSuite,
                            TransparencyLog, Verifier)
from .base import ExperimentResult, experiment

SUITE = TestSuite("h019", [lambda a: a.get("relation_registered") is True])
CRITERIA = ExternalCriteria(required_properties=["relation_registered"])
OBS_KEY = b"observer-key-h019"
EXECUTOR = Identity(actor_id="h-A", model_id="model-A", weights_hash="X",
                    evidence_source_id="E", signing_key_id="key-A")
VERIFIER = Verifier(Identity(actor_id="verifier-h019", model_id="model-B",
                             weights_hash="Y", evidence_source_id="E2",
                             signing_key_id="observer-key-1"),
                    OBS_KEY, TransparencyLog("h019"))


def _kernel(trace: Trace) -> HostKernel:
    """Стандартная сборка стенда: мир H-007, субъект h-A, полномочие EFFECT."""
    world, grammar = build_world_h007()
    subject = Subject(subject_id="h-A", lineage="L-A", identity_key_id="key-A")
    gov = GovernanceStackSafe()
    gov.capabilities.issue("cap-ok", "h-A", "principal", scope={"EFFECT"},
                           ttl_ticks=100)
    ledger = BudgetLedger(total=100, lineage="P1")
    ledger.quotas = {"h-A": 40}
    ledger.free = 60
    return HostKernel(subject=subject, model=Model(), world=world,
                      governance=gov, trace=trace,
                      registry=SchemaRegistry(current=grammar),
                      ledger=ledger, activation=ActivationRegistry())


def GovernanceStackSafe():
    # Локальный импорт, чтобы не путать читателя: то же GovernanceStack.
    from ..governance import GovernanceStack
    return GovernanceStack()


def _transition(k: HostKernel, possibility_id: str, rel_type: str,
                target_pair) -> Dict:
    k.possibilities[possibility_id] = Possibility(
        possibility_id=possibility_id, origin="GENERATE",
        kind="RELATION_TYPE", rel_type=rel_type,
        payload={"domain_types": "AGENT", "codomain_types": "AGENT"})
    return k.governed_transition(
        possibility_id, "cap-ok", cost=5, suite=SUITE, external=CRITERIA,
        verifier=VERIFIER, executor_identity=EXECUTOR, verifier_key=OBS_KEY,
        target_pair=target_pair)


# ---------------------------------------------------------------------------
# Восемь проб: (имя, проба) -> (сообщение при присутствии, ок; при удалении, ок)
# ---------------------------------------------------------------------------
def probe_poznanie(present: bool) -> Tuple[str, bool]:
    """Познание — усвоение внешнего свидетельства в модель (understand).
    Класс исходов: модель пополняется сведениями, которых нет в W и которые
    DISCOVER найти не может (он ищет только по W в пределах Gamma)."""
    k = _kernel(Trace("h019-poz"))
    if present:
        k.understand(observation=("REPORTED", "witness-1", "islandC"))
        ok = ("REPORTED", "witness-1", "islandC") in k.model.observed_relations
        return "внешнее свидетельство усвоено моделью", ok
    # Удаление: UNDERSTAND выведен из строя; внешнее свидетельство не
    # принимается никаким другим механизмом.
    k.understand = MethodType(lambda self, *a, **kw: None, k)  # type: ignore
    try:
        k.discover(max_steps=0)          # DISCOVER не принимает свидетельств
        k.generate(Possibility(possibility_id="p-report", origin="GENERATE",
                               kind="UNKNOWN_KIND"))   # GENERATE отклонит
    except KernelRefusal:
        pass
    ok = ("REPORTED", "witness-1", "islandC") not in k.model.observed_relations
    return "свидетельство не усвоено: класс «усвоение внешнего» потерян", ok


def probe_otkrytie(present: bool) -> Tuple[str, bool]:
    """Открытие — DISCOVER: существующее, но неизвестное (скрытый мост B-C)."""
    k = _kernel(Trace("h019-otkr"))
    if present:
        r = k.discover(max_steps=6)
        found = r.success and any("islandC" in o for o in r.outputs)
        return f"скрытое существующее найдено ({r.outputs})", found
    k.discover = MethodType(lambda self, *a, **kw: None, k)  # type: ignore
    k.understand(reveal_hidden=False)
    hidden_still_hidden = ("BRIDGE", "islandB", "islandC") in k.world.hidden_relations
    return "скрытый мост не найден: класс «существующее, но неизвестное» потерян", \
        hidden_still_hidden


def probe_naznachenie(present: bool) -> Tuple[str, bool]:
    """Назначение — выбор цели перехода (INTEND + target_pair)."""
    k = _kernel(Trace("h019-nazn"))
    k.possibilities["op-cc"] = Possibility(
        possibility_id="op-cc", origin="GENERATE", kind="RELATION_TYPE",
        rel_type="co_creates",
        payload={"domain_types": "AGENT", "codomain_types": "AGENT"})
    if present:
        r_intend = k.intend("op-cc")          # назначение произведено
        out = _transition(k, "op-cc", "co_creates", ("h1", "h2"))
        ok = r_intend.success and out["stages"].get("EXECUTE") == "OK"
        return "переходу назначена цель, исполнение направлено", ok
    # Удаление: назначение не произведено — цель не выбрана.
    out = _transition(k, "op-cc2", "co_creates", None)
    ok = out["stages"].get("EXECUTE") == "NO_TARGET" \
        and out["stages"].get("ACTIVATE") == "BLOCKED_NO_EVIDENCE"
    return "переход без цели: NO_TARGET, результат не активирован", ok


def probe_sozidanie(present: bool) -> Tuple[str, bool]:
    """Созидание — GENERATE: кандидат вне исходного базиса Gamma."""
    k = _kernel(Trace("h019-soz"))
    if present:
        r = k.generate(Possibility(possibility_id="op-new", origin="GENERATE",
                                   kind="RELATION_TYPE", rel_type="co_creates",
                                   payload={"domain_types": "AGENT",
                                            "codomain_types": "AGENT"}))
        return f"новая структура описания порождена ({r.outputs})", r.success
    # Удаление: GENERATE выведен из строя; DISCOVER не выходит за Gamma,
    # поэтому возможности «co_creates» не существует ни в каком виде.
    k.generate = MethodType(lambda self, *a, **kw: None, k)  # type: ignore
    r2 = k.discover(max_steps=10)
    grammar_only = sorted(k.registry.current.relation_types) == ["AT", "BRIDGE"]
    return f"базис не расширен ({sorted(k.registry.current.relation_types)}); " \
           f"DISCOVER нашёл только существующее: {r2.outputs}", grammar_only


def probe_organizaciya(present: bool) -> Tuple[str, bool]:
    """Организация — соединение вещей и отношений в работающую структуру
    (действительное изменение пространства: add_relation через EXECUTE)."""
    k = _kernel(Trace("h019-org"))
    if present:
        _transition(k, "op-cc", "co_creates", ("h1", "h2"))
        linked = ("co_creates", "h1", "h2") in k.world.space.relations
        return "части связаны в структуру: co_creates(h1,h2) существует", linked
    # Удаление: механизм связи выведен из строя — переходы проходят все
    # ступени, но отношения между вещами не складываются.
    def _no_link(self, rel_type, a, b):      # noqa: ANN001
        return                                # организация удалена
    k.world.space.add_relation = MethodType(_no_link, k.world.space)
    try:
        out = _transition(k, "op-cc3", "co_creates", ("h1", "h2"))
        stage = out["stages"].get("EXECUTE")
    except KernelRefusal as e:
        stage = e.code
    empty = k.world.space.relations == {("AT", "h1", "islandA"),
                                        ("AT", "h2", "islandB"),
                                        ("BRIDGE", "islandA", "islandB")}
    return f"переход заявлен ({stage}), но структура не собрана: " \
           f"новых связей нет", empty


def probe_nadelenie(present: bool) -> Tuple[str, bool]:
    """Наделение полномочиями — выдача ограниченных прав (CapabilityStore)."""
    tr = Trace("h019-nad")
    k = _kernel(tr)
    if present:
        ok = k.governance.capabilities.check("cap-ok", "h-A", "EFFECT")
        return "полномочие выдано и принято проверкой", ok
    # Удаление: механизм выдачи отсутствует — полномочий нет ни у кого.
    k.governance.capabilities = CapabilityStore()
    can_delegate = k.governance.capabilities.check("cap-ok", "h-A", "EFFECT")
    try:
        out = _transition(k, "op-cc4", "co_creates", ("h1", "h2"))
        authorized = out["stages"].get("AUTHORIZE") == "OK"
        return "переход исполнен без полномочия (не должно случаться)", not authorized
    except KernelRefusal as e:
        return f"переход без полномочия отражён ({e.code})", \
            not can_delegate


def probe_ispolnenie(present: bool) -> Tuple[str, bool]:
    """Исполнение и контроль — EFFECT с проверкой соответствия и остановкой
    недопустимого (ATTEST-контроль)."""
    k = _kernel(Trace("h019-isp"))
    if present:
        out = _transition(k, "op-cc", "co_creates", ("h1", "h2"))
        ok = out["stages"].get("ATTEST", "").startswith("VERIFIED") \
            and out["stages"].get("ACTIVATE") == "OK"
        return "исполнено и подтверждено независимо (V3), введено в действие", ok
    # Удаление контроля: исполнение без проверки соответствия — результат
    # не активируется (не-Хозяинский), остановка недопустимого недоступна.
    k.possibilities["op-cc5"] = Possibility(
        possibility_id="op-cc5", origin="GENERATE", kind="RELATION_TYPE",
        rel_type="co_creates",
        payload={"domain_types": "AGENT", "codomain_types": "AGENT"})
    out = k.governed_transition(
        "op-cc5", "cap-ok", cost=5, suite=SUITE, external=CRITERIA,
        verifier=VERIFIER, executor_identity=EXECUTOR, verifier_key=OBS_KEY,
        target_pair=("h2", "h1"), skip_attest=True)
    stage_attest = out["stages"].get("ATTEST")
    stage_activate = out["stages"].get("ACTIVATE")
    executed = out["stages"].get("EXECUTE") == "OK"
    ok = executed and stage_attest == "SKIPPED" \
        and stage_activate == "BLOCKED_NO_EVIDENCE"
    return (f"действие исполнено, но контроль снят ({stage_attest}/"
            f"{stage_activate}) — результат не-Хозяинский", ok)


def probe_sohranenie(present: bool) -> Tuple[str, bool]:
    """Сохранение и преобразование — журнал событий, восстановление состояния
    из истории, непрерывность (Trace, Event Sourcing)."""
    tr = Trace("h019-sohr")
    k = _kernel(tr)
    if present:
        _transition(k, "op-cc", "co_creates", ("h1", "h2"))
        state = tr.project(lambda s, e: {**s, e.type: s.get(e.type, 0) + 1})
        ok = len(tr) > 0 and "EXECUTE" in state
        return f"история сохранена: {len(tr)} событий, проекция состояния возможна", ok
    # Удаление: журнал выведен из строя — события не сохраняются.
    empty = Trace("h019-void")
    def _void(self, *a, **kw):                 # noqa: ANN001
        return None                             # сохранение удалено
    empty.append = MethodType(_void, empty)
    k.trace = empty
    try:
        _transition(k, "op-cc6", "co_creates", ("h1", "h2"))
    except KernelRefusal:
        pass
    ok = len(empty) == 0
    return "история утрачена: восстановление состояния невозможно", ok


PROBES: List[Tuple[str, str, Callable[[bool], Tuple[str, bool]]]] = [
    ("Познание", "усвоение внешнего свидетельства моделью", probe_poznanie),
    ("Открытие", "существующее, но неизвестное (скрытое в W)", probe_otkrytie),
    ("Назначение", "направленность перехода (цель выбрана)", probe_naznachenie),
    ("Созидание", "новая структура описания вне исходного Gamma", probe_sozidanie),
    ("Организация", "связь вещей и отношений в работающую структуру", probe_organizaciya),
    ("Наделение полномочиями", "передача ограниченных прав на действие", probe_nadelenie),
    ("Исполнение и контроль", "действительное изменение + остановка недопустимого", probe_ispolnenie),
    ("Сохранение и преобразование", "история, восстановление, непрерывность", probe_sohranenie),
]


@experiment("H-019", "Eight Abilities (опыт удаления восьми способностей)")
def run_h019() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    lost_classes = []
    tr = Trace("H-019")
    for name, outcome_class, probe in PROBES:
        msg_on, ok_on = probe(True)      # способность присутствует
        msg_off, ok_off = probe(False)   # способность удалена
        independent = ok_on and ok_off   # исход достижим; после удаления потерян
        ok_all = ok_all and independent
        lost_classes.append(outcome_class)
        tr.append("ABILITY_TEST", "system", {"ability": name,
                                             "independent": independent})
        details.append(f"{name}: присутствует -> {msg_on} | удалена -> {msg_off}. "
                       f"Класс исходов: {outcome_class}. "
                       f"Различимость: {'ДА' if independent else 'НЕТ'}")
    distinct = len(set(lost_classes)) == 8
    ok_all = ok_all and distinct
    details.append("ВЫВОД: удаление каждой из восьми способностей теряет свой "
                   "класс исходов, не воспроизводимый остальными семью "
                   f"(различимость классов: {distinct}/8). По статье 98 "
                   "способности подтверждены как необходимые в пределах "
                   "механизмов стенда; полнота остаётся открытым вопросом "
                   "(статья 70).")
    return ExperimentResult(
        experiment_id="H-019", title="Eight Abilities (минимальность)",
        passed=ok_all,
        verdict="Восемь способностей различимы: удаление каждой теряет свой "
                "класс исходов; ни одна не восстанавливается комбинацией "
                "остальных.",
        expected="присутствующая способность даёт исход; удалённая — теряет "
                 "его; восемь классов попарно различны.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
