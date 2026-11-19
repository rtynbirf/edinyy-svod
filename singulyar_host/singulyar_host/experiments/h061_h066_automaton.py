# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.3 — Х-061..Х-066: фронт X (автоматность).
Конституция, Таблица 5 (фронт X); модуль automaton.py.
"""
from __future__ import annotations

from typing import List

from ..automaton import (
    EVENTS,
    STATES,
    TRANSITIONS,
    HouseAutomaton,
    MachineRecord,
    _refusal,
    fold,
)
from ..trace import Trace
from .base import ExperimentResult, experiment


@experiment("Х-061", "Полнота таблицы: дыра в клетке — дефект сборки (фронт X)")
def run_h061() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("Х-061")
    a = HouseAutomaton()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("COVERAGE_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    cov = a.coverage()
    record("таблица полна: 8 состояний × 12 событий = 96 клеток",
           cov["клеток"] == 96 and cov["дыр"] == 0 and cov["переходов"] > 0,
           f"переходов {cov['переходов']}, именованных запретов {cov['запретов']}, "
           f"дыр {cov['дыр']} (Ф-X-2, Х-061)")

    # Искусственная дыра: вынуть настоящий переход — пара падает в цепь запретов
    # без ветки, обход обязан назвать её дырой и отказать сборке.
    shadow = dict(TRANSITIONS)
    shadow.pop(("ЗАЯВЛЕНО", "ПРОГОН"))
    holes = 0
    for s in STATES:
        for e in EVENTS:
            if (s, e) not in shadow:
                try:
                    _refusal(s, e)
                except AssertionError:
                    holes += 1
    record("вынутый переход обнаружен обходом", holes == 1,
           f"таблица без одного перехода даёт {holes} дыр — сборка отказана (Ф-X-2, Х-061)")

    return ExperimentResult(
        experiment_id="Х-061", title="Полнота таблицы (Х-061, фронт X)",
        passed=ok_all,
        verdict="Каждая пара (состояние, событие) покрыта переходом или "
                "именованным запретом; вынутая клетка обнаруживается обходом "
                "(Ф-X-2, Х-061).",
        expected="96/96 клеток; дыра в таблице — дефект сборки, не поведение.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("Х-062", "Детерминизм: одна голова + одно событие = один исход (фронт X)")
def run_h062() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("Х-062")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("DETERMINISM_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    script = [
        ("ПРИГОВОР", "ЗАЯВЛЕНО"),
        ("ПРОГОН", "ВЫПОЛНЕНО"),
        ("САМОПОДТВЕРЖДЕНИЕ", None),          # запрет — голова не меняется
        ("НЕЗАВИСИМАЯ_ПРОВЕРКА", "ПОДТВЕРЖДЕНО"),
        ("ЗНАЧИМОЕ_ИЗМЕНЕНИЕ", "НЕ ПРОВЕРЕНО"),
    ]

    def run_script() -> List[MachineRecord]:
        m = HouseAutomaton()
        for ev, _exp in script:
            m.step(m.head, ev)
        return m.journal

    # 1000 повторов той же последовательности — тот же журнал и та же голова.
    first = run_script()
    head0 = fold(first)
    same = all(
        [(r.state, r.event, r.verdict, r.to_state) for r in run_script()]
        == [(r.state, r.event, r.verdict, r.to_state) for r in first]
        for _ in range(1000)
    )
    record("1000 повторов — тот же журнал и голова", same and head0 == "НЕ ПРОВЕРЕНО",
           f"голова после сценария: {head0}; расхождений нет (Ф-X-3, Х-062)")

    # Запрет не меняет голову, но пишется в журнал (не проходит молча).
    m2 = HouseAutomaton()
    m2.step(m2.head, "ПРОГОН")                 # НЕ ПРОВЕРЕНО -> ВЫПОЛНЕНО
    rec = m2.step(m2.head, "САМОПОДТВЕРЖДЕНИЕ")
    record("запрет именуется и пишется, голову не двигает",
           rec.verdict == "ЗАПРЕТ" and m2.head == "ВЫПОЛНЕНО"
           and rec.note.startswith("SELF_CONFIRMATION"),
           "попытка самоподтверждения записана, статус остался ВЫПОЛНЕНО "
           "(ст. 77/84, Х-062)")

    return ExperimentResult(
        experiment_id="Х-062", title="Детерминизм автомата (Х-062, фронт X)",
        passed=ok_all,
        verdict="Одна голова и одно событие дают один исход; тысяча повторов "
                "неразличима; запрет пишется, но голову не двигает (Ф-X-3, Х-062).",
        expected="одинаковый журнал во всех прогонах; запрет без движения головы.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("Х-063", "Незаписанный переход не существует; голова — свёртка журнала (фронт X)")
def run_h063() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("Х-063")
    a = HouseAutomaton()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("REPLAY_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    a.step(a.head, "ПРИГОВОР")     # -> ЗАЯВЛЕНО
    a.step(a.head, "ПРОГОН")       # -> ВЫПОЛНЕНО

    # 1. Событие вне таблицы не меняет голову, попытка записана.
    rec = a.step(a.head, "ВЗМАХ РУКОЙ")
    record("событие вне таблицы — запрет и запись",
           rec.verdict == "НЕИЗВЕСТНОЕ_СОБЫТИЕ" and a.head == "ВЫПОЛНЕНО",
           "«взмах рукой» записан как попытка, голова не сдвинулась (Ф-X-2, Х-063)")

    # 2. Голова = fold(журнал); посторонняя «правда» без записи — подмена.
    claimed = "ПОДТВЕРЖДЕНО"       # кто-то объявил подтверждение без записи
    record("правка без события — подмена отпечатка",
           fold(a.journal) != claimed and fold(a.journal) == "ВЫПОЛНЕНО",
           f"журнал даёт {fold(a.journal)}, заявлено {claimed} — расхождение "
           f"фиксируется (Ф-X-1, Х-063)")

    # 3. Полная реплика: тот же журнал даёт ту же голову (новая сессия).
    b = HouseAutomaton()
    for r in a.journal:
        b.step(r.state, r.event)
    record("реплика из журнала воспроизводит голову",
           fold(b.journal) == fold(a.journal) and len(b.journal) == len(a.journal),
           f"{len(a.journal)} записей → {fold(b.journal)} (Ф-X-1, Х-063)")

    return ExperimentResult(
        experiment_id="Х-063", title="Незаписанный переход (Х-063, фронт X)",
        passed=ok_all,
        verdict="Событие вне таблицы не двигает голову и записывается; голова "
                "равна свёртке журнала; правка без события — подмена (Ф-X-1..2, Х-063).",
        expected="голова = fold(журнал); незаписанное не существует.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("Х-064", "Достижимость: мёртвое состояние — дефект сборки (фронт X)")
def run_h064() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("Х-064")
    a = HouseAutomaton()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("REACH_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    reach = a.reachability()
    record("все восемь состояний достижимы",
           reach["достижимых"] == reach["всего"] and not reach["мёртвые"],
           "обход из НЕ ПРОВЕРЕНО покрывает 8/8 (Ф-X-5, Х-064)")

    # Круг статуса по реальным переходам: НЕ ПРОВЕРЕНО → ЗАЯВЛЕНО → ВЫПОЛНЕНО
    # → ПОДТВЕРЖДЕНО → ОСПОРЕНО → НЕ ПРОВЕРЕНО (полный круг статуса).
    m = HouseAutomaton()
    path = ["ПРИГОВОР", "ПРОГОН", "НЕЗАВИСИМАЯ_ПРОВЕРКА", "ПРОТИВОРЕЧИЕ",
            "ЗНАЧИМОЕ_ИЗМЕНЕНИЕ"]
    heads = [m.head]
    for ev in path:
        m.step(m.head, ev)
        heads.append(m.head)
    record("круг статуса проходим объявленными переходами",
           heads == ["НЕ ПРОВЕРЕНО", "ЗАЯВЛЕНО", "ВЫПОЛНЕНО", "ПОДТВЕРЖДЕНО",
                     "ОСПОРЕНО", "НЕ ПРОВЕРЕНО"],
           " -> ".join(heads) + " (ст. 68, фронт V; Х-064)")

    # Вынутый переход делает состояние недостижимым — сборка обязана отказаться.
    shadow = dict(TRANSITIONS)
    shadow.pop(("ВЫПОЛНЕНО", "НЕЗАВИСИМАЯ_ПРОВЕРКА"))
    seen = {"НЕ ПРОВЕРЕНО"}
    frontier = ["НЕ ПРОВЕРЕНО"]
    while frontier:
        cur = frontier.pop()
        for e in EVENTS:
            nxt = shadow.get((cur, e))
            if nxt is not None and nxt[0] not in seen:
                seen.add(nxt[0])
                frontier.append(nxt[0])
    record("вынутый переход улавливается обходом", "ПОДТВЕРЖДЕНО" not in seen,
           "ПОДТВЕРЖДЕНО стало мёртвым — сборка отказана (Ф-X-5, Х-064)")

    return ExperimentResult(
        experiment_id="Х-064", title="Достижимость состояний (Х-064, фронт X)",
        passed=ok_all,
        verdict="8/8 состояний достижимы; круг статуса проходим; вынутый переход "
                "делает состояние мёртвым и обнаруживается (Ф-X-5, Х-064).",
        expected="полный обход; мёртвое состояние — дефект сборки.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("Х-065", "Сериализация: два события к одной голове — по очереди (фронт X)")
def run_h065() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("Х-065")
    a = HouseAutomaton()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("SERIAL_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # Два события «одновременно» к одной голове: ПРИГОВОР и САМОПОДТВЕРЖДЕНИЕ.
    # Автомат сериализует: второе судится по новой голове первого.
    r1 = a.step(a.head, "ПРИГОВОР")              # НЕ ПРОВЕРЕНО -> ЗАЯВЛЕНО
    r2 = a.step(a.head, "САМОПОДТВЕРЖДЕНИЕ")     # ЗАЯВЛЕНО -> запрет
    record("второе событие судится по новой голове",
           r1.verdict == "ПЕРЕХОД" and r2.verdict == "ЗАПРЕТ"
           and r2.state == "ЗАЯВЛЕНО" and a.head == "ЗАЯВЛЕНО",
           "самоподтверждение отклонено уже в ЗАЯВЛЕНО: слияния нет (Ф-X-7, Х-065)")

    # Обратный порядок даёт другой приговор — порядок фиксирует журнал.
    b = HouseAutomaton()
    rb1 = b.step(b.head, "САМОПОДТВЕРЖДЕНИЕ")    # НЕ ПРОВЕРЕНО -> запрет
    rb2 = b.step(b.head, "ПРИГОВОР")             # НЕ ПРОВЕРЕНО -> ЗАЯВЛЕНО
    record("порядок событий значим и закреплён записью",
           rb1.verdict == "ЗАПРЕТ" and rb2.verdict == "ПЕРЕХОД"
           and fold(b.journal) == "ЗАЯВЛЕНО"
           and [x.event for x in b.journal] == ["САМОПОДТВЕРЖДЕНИЕ", "ПРИГОВОР"],
           "тот же набор событий, другой порядок — другой след в журнале, "
           "голова та же (Ф-X-7, Х-065)")

    # Ничья между событиями не признаётся: журнал линейный.
    seqs = [x.seq for x in a.journal]
    record("журнал линеен, без раздвоения головы",
           seqs == sorted(seqs) and len(set(seqs)) == len(seqs),
           f"последовательность {seqs} (Ф-X-7, Х-065)")

    return ExperimentResult(
        experiment_id="Х-065", title="Сериализация событий (Х-065, фронт X)",
        passed=ok_all,
        verdict="Два события к одной голове применяются по очереди; второе судится "
                "по новой голове первого; журнал линеен, слияния нет (Ф-X-7, Х-065).",
        expected="без гонок и слияний; порядок закреплён записью.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("Х-066", "Человек вне автомата: воля — не событие (фронт X)")
def run_h066() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("Х-066")
    a = HouseAutomaton()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("HUMAN_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # 1. «Воля без записи» из любого состояния — именованный запрет.
    m = HouseAutomaton()
    m.step(m.head, "ПРИГОВОР")
    rec = m.step(m.head, "ВОЛЯ_БЕЗ_ЗАПИСИ")
    record("воля без записи — запрет", rec.verdict == "ЗАПРЕТ"
           and rec.note.startswith("WILL_WITHOUT_RECORD") and m.head == "ЗАЯВЛЕНО",
           "ст. 1, 62/фронт VIII: воля входит приговором, а не событием (Ф-X-8, Х-066)")

    # 2. Тишина не вскрывает: МОЛЧАНИЕ_БЕЗ_ЗАПИСИ — запрет во всех состояниях.
    silence_all = all(
        TRANSITIONS.get((s, "МОЛЧАНИЕ_БЕЗ_ЗАПИСИ")) is None for s in STATES)
    m2 = HouseAutomaton()
    m2.step(m2.head, "ПРОГОН")
    rec2 = m2.step(m2.head, "МОЛЧАНИЕ_БЕЗ_ЗАПИСИ")
    record("тишина не переводит статус",
           silence_all and rec2.verdict == "ЗАПРЕТ"
           and rec2.note.startswith("SILENCE_NOT_KEYS") and m2.head == "ВЫПОЛНЕНО",
           "фронт IX: молчание не вскрывает; эпоха тишины — объявленный ход "
           "фронта III, не событие статуса (Ф-X-8, Х-066)")

    # 3. Воля человека проходит в дом только приговором полного состава —
    #    с вынесшим, областью и записью; приговор — единственная дверь воли.
    m3 = HouseAutomaton()
    m3.step(m3.head, "ВОЛЯ_БЕЗ_ЗАПИСИ")          # запрет
    m3.step(m3.head, "СЛОВО_БЕЗ_ОБЛАСТИ")        # запрет
    m3.step(m3.head, "ПРИГОВОР")                 # воля — приговором
    bad = [x for x in m3.journal if x.verdict != "ПЕРЕХОД"]
    record("воля — только приговором полного состава",
           len(bad) == 2 and m3.head == "ЗАЯВЛЕНО"
           and m3.journal[-1].verdict == "ПЕРЕХОД",
           "две попытки записаны как запреты; приговор принят (ст. 68, Х-036; Ф-X-8, Х-066)")

    return ExperimentResult(
        experiment_id="Х-066", title="Человек вне автомата (Х-066, фронт X)",
        passed=ok_all,
        verdict="Воля без записи и тишина — именованные запреты; воля человека "
                "входит в дом приговором полного состава, а не событием "
                "(Ф-X-8, Х-066).",
        expected="вне автомата: человек ждёт записи; автомат ждёт приговора.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
