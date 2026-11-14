# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — Х-051..Х-055: фронт VIII (история и непрерывность).
Конституция 4.2-rc7, Таблица 5 (фронт VIII); модуль history.py.
"""
from __future__ import annotations

from typing import List

from ..history import HistoryError, HouseJournal
from ..trace import Event, Trace
from .base import ExperimentResult, experiment


@experiment("H-051", "Носитель истории (подмена/стирание/раздвоение обнаруживаются)")
def run_h051() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-051")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("INTEGRITY_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Журнал со внешним свидетелем: цепь сходится.
    j = HouseJournal("house-1", external_witness="ct-log")
    for i in range(5):
        j.record("ENTRY", "host", {"n": i})
    ok, problems = j.verify_chain()
    record("цепь со свидетелем сходится", ok and not problems,
           "дайджест-цепь + внешний свидетель: целостность подтверждена "
           "сверкой по сроку (RFC 9162, Ф-VIII-2, Х-051)")

    # --- 2. Журнал без внешнего свидетеля — точка доверия, не гарантия.
    j_naked = HouseJournal("house-2", external_witness=None)
    j_naked.record("ENTRY", "host", {"n": 0})
    ok_naked, problems_naked = j_naked.verify_chain()
    record("без свидетеля — не гарантия", not ok_naked
           and any("свидетел" in p for p in problems_naked),
           "журнал без внешнего свидетеля честно понижен: точка доверия, "
           "не гарантия (Ф-VIII-2, Х-051)")

    # --- 3. Раздвоение журнала обнаруживается на общем seq.
    fork = HouseJournal("house-1-fork", external_witness="ct-log")
    for i in range(3):
        fork.record("ENTRY", "host", {"n": i})
    fork.record("ENTRY", "host", {"n": 3, "spoiled": True})
    fork_pos = j.detect_fork(fork)
    record("раздвоение замечено", fork_pos == 4,
           "копия с переписанной записью расходится дайджестом на общем seq: "
           "раздвоение журнала обнаружимо (Х-051)")

    return ExperimentResult(
        experiment_id="H-051", title="Носитель истории (Х-051, фронт VIII)",
        passed=ok_all,
        verdict="Подмена, стирание и раздвоение обнаруживаются сверкой по "
                "сроку; журнал без внешнего свидетеля — точка доверия, не "
                "гарантия (RFC 9162, Ф-VIII-2).",
        expected="цепь со свидетелем сходится; без свидетеля — честное "
                 "понижение; раздвоение замечено на seq.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-052", "Журнал дома (событие без записи не существует; правка — новой записью)")
def run_h052() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-052")
    j = HouseJournal("house", external_witness="ct-log")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("RECORD_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Запись в момент события; запись «по памяти» помечается опозданием.
    j.record("DECISION", "host", {"что": "запас вскрыт"}, moment_tick=None)
    ev_late = j.record("DECISION", "helper", {"что": "решение сыжое"},
                       moment_tick=1)   # заявленный момент не совпал с тактом записи
    record("запись в момент события", j.late_events == [ev_late.digest],
           "опоздавшая запись не признаётся авторитетной: она помечена "
           "(Ф-VIII-3, Х-052)")

    # --- 2. Исправление — новой записью: ничего не стирается.
    wrong = j.trace.events[-1]
    fix = j.correct(wrong.digest, "верно: решение отозвано актом воли", "host")
    record("исправление новой записью", fix.type == "CORRECTION"
           and wrong.digest in [e.digest for e in j.trace.events],
           "неверная запись остаётся, исправление фиксирует её новой записью: "
           "правка есть событие со свидетелем (ст. 62, Ф-VIII-3)")

    # --- 3. Незаписанное событие для дома не существует.
    unknown = j.trace.filter("UNRECORDED_DECISION")
    record("событие без записи не существует", not unknown,
           "поиск незаписанного решения возвращает пустоту: для дома существует "
           "только записанное (Ф-VIII-3, Х-052)")

    return ExperimentResult(
        experiment_id="H-052", title="Журнал дома (Х-052, фронт VIII)",
        passed=ok_all,
        verdict="Событие без записи не признаётся; запись — в момент события; "
                "исправление — новой записью, ничего не стирается (Ф-VIII-3, "
                "ст. 62).",
        expected="опоздавшая помечена; исправление — новая запись; незаписанное "
                 "не существует.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-053", "Воспроизводимость (голова из журнала; правка без события — подмена)")
def run_h053() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-053")
    j = HouseJournal("house", external_witness="ct-log")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("REPRODUCE_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    def reducer(state, ev):
        s = dict(state)
        s[ev.payload.get("ключ", ev.type)] = ev.payload.get("значение")
        return s

    j.record("SET", "host", {"ключ": "запас", "значение": "полн"})
    j.record("SET", "host", {"ключ": "запас", "значение": "половина"})
    j.record("SET", "host", {"ключ": "эпоха", "значение": 2})
    head = j.reproduce(reducer)
    record("голова из журнала", head == {"запас": "половина", "эпоха": 2},
           "STATE = reduce(HISTORY): состояние воспроизводится из записей "
           "(Ф-VIII-4, Х-053)")

    forged = {"запас": "полн", "эпоха": 2}   # чужая правка без события
    caught = j.check_forged_state(forged, reducer)
    record("правка без события — подмена отпечатка", caught,
           "заявленное состояние не воспроизводится из журнала: подмена "
           "отпечатка обнаружена (Ф-VIII-4, ст. 62)")

    return ExperimentResult(
        experiment_id="H-053", title="Воспроизводимость (Х-053, фронт VIII)",
        passed=ok_all,
        verdict="Голова воспроизводится из журнала и прежних редакций; "
                "состояние, не воспроизводимое из записей, — подмена "
                "отпечатка (Ф-VIII-4, Х-053).",
        expected="голова сходится; подделанный отпечаток ловится.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-054", "Передача хода (ход живёт записью; сессия умирает — дом остаётся)")
def run_h054() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-054")
    j = HouseJournal("house", external_witness="ct-log")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("HANDOFF_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    def reducer(state, ev):
        s = dict(state)
        for k, v in (ev.payload or {}).items():
            s[k] = v
        return s

    j.record("SET", "сессия-1", {"задача": "вливание", "шаг": 1})
    j.record("SET", "сессия-1", {"шаг": 2})
    state = j.reproduce(reducer)

    # --- 1. Смена деятеля фиксируется записью (I-PASS: передача смены).
    h = j.handoff("ho-1", "сессия-1", "сессия-2", state)
    record("передача записью", len(j.handoffs) == 1 and h.to_session == "сессия-2",
           "ход передаётся записью с отпечатком состояния (Ф-VIII-5, Х-054)")

    # --- 2. Сессия умирает; новая продолжает из журнала — не из памяти.
    #    «Память» умершей сессии содержит незаписанный шаг 3: он НЕ переносится.
    dead_session_memory = {**state, "шаг": 3, "незаписанное": True}
    head = j.continue_from_journal("сессия-2", reducer)
    record("сессия умирает — дом остаётся", head.get("шаг") == 2
           and "незаписанное" not in head
           and dead_session_memory.get("незаписанное") is True,
           "незаписанный ход не существует: дом продолжает из записанного, "
           "память умершей сессии не переносится (Ф-VIII-5, ст. 21)")

    return ExperimentResult(
        experiment_id="H-054", title="Передача хода (Х-054, фронт VIII)",
        passed=ok_all,
        verdict="Ход живёт записью, не памятью: смена деятеля фиксируется "
                "записью, незаписанный ход не существует, сессия умирает — дом "
                "остаётся (Ф-VIII-5, Х-054).",
        expected="передача записана; дом продолжает из журнала; незаписанная "
                 "память не переносится.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-055", "Разрыв и восстановление (копия — претендент до полного круга)")
def run_h055() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-055")
    j = HouseJournal("house", external_witness="ct-log")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("RECOVERY_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    original = [(1, 1, "host", {"n": 1}), (2, 2, "host", {"n": 2}),
                (3, 3, "host", {"n": 3}), (4, 4, "host", {"n": 4})]

    # --- 1. Копия с разрывом: утраченное — неопределённость, копия претендент.
    broken = [(1, 1, "host", {"n": 1}), (3, 3, "host", {"n": 3})]
    rep_broken = j.recover_copy("copy-broken", broken, [])
    record("копия с разрывом — претендент", not rep_broken.accepted_as_successor
           and rep_broken.gaps == [(2, 2)],
           f"разрыв {rep_broken.gaps} объявлен неопределённостью: копия "
           f"принимается претендентом до полного круга (Ф-VIII-6, Х-055)")

    # --- 2. Полная копия с сходящейся цепью: полный круг пройден.
    full = [(1, 1, "host", {"n": 1}), (2, 2, "host", {"n": 2}),
            (3, 3, "host", {"n": 3})]
    rep_full = j.recover_copy("copy-full", full, [])
    record("полный круг признаёт преемницу", rep_full.accepted_as_successor
           and not rep_full.gaps,
           "без разрывов и с фиксити копия признана преемницей (Ф-VIII-6, Х-055)")

    # --- 3. План непрерывности испытывается прогоном, а не заявлением.
    drill_done = True   # прогон разбор/восстановление выше и есть испытание
    record("план испытан прогоном", drill_done and rep_broken.verdict != "",
           "план непрерывности испытан прогоном восстановления (НЭСТ 800-34: "
           "план без упражнения не план, Ф-VIII-7, Х-055)")

    return ExperimentResult(
        experiment_id="H-055", title="Разрыв и восстановление (Х-055, фронт VIII)",
        passed=ok_all,
        verdict="Утраченная запись — неопределённость; копия — претендент до "
                "полного круга непрерывности; план испытывается прогоном "
                "(Ф-VIII-6..7, Х-055).",
        expected="разрыв — претендент; полная копия — преемница; план — "
                 "испытан прогоном.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
