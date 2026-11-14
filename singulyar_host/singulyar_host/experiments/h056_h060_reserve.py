# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — Х-056..Х-060: фронт IX (запас).
Конституция 4.2-rc7, Таблица 5 (фронт IX); модуль reserve.py.
"""
from __future__ import annotations

from typing import List

from ..reserve import ReserveError, ReserveItem, ReservePool
from ..trace import Trace
from .base import ExperimentResult, experiment


@experiment("H-056", "Мера и пол (дни автономности; расход ниже пола отклоняется)")
def run_h056() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-056")
    pool = ReservePool()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("FLOOR_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    for i in range(10):
        pool.receive(ReserveItem(f"fuel-{i}", "топливо", 10.0, "ед",
                                 expires_tick=100, hazard_class="сбой питания",
                                 location="склад-1", recorded_tick=0))
    pool.set_burn("топливо", per_day=20.0)

    # --- 1. Мера: дни автономности при названном расходе.
    days = pool.autonomy_days("топливо")
    record("мера — дни автономности", abs(days - 5.0) < 1e-9,
           "100 ед / 20 ед-в-сутки = 5 суток автономности (Ф-IX-2, Х-056)")

    # --- 2. Пол поставлен явным решением; расход ниже пола отклоняется.
    pool.set_floor("топливо", floor=40.0, by="principal", decision_id="D-1")
    below = []
    try:
        pool.consume("c-1", "топливо", 70.0, "helper")   # 100-70=30 < 40
    except ReserveError as e:
        below.append(e)
    record("расход ниже пола отклоняется", bool(below)
           and "BELOW_FLOOR" in str(below[0]),
           "неснижаемый остаток 40: расход 70 отклонён (Ф-IX-2, Х-056)")

    # --- 3. Ноль пола — только явным решением, записанным.
    pool2 = ReservePool()
    no_decision = pool2.zero_floor_without_decision("топливо")
    pool2.set_floor("топливо", floor=0.0, by="principal", decision_id="D-0")
    decided = not pool2.zero_floor_without_decision("топливо")
    record("ноль — явным решением", no_decision and decided,
           "ноль неснижаемого остатка не наступает молчанием: только записанным "
           "решением Хозяина (Ф-IX-2, Х-056)")

    return ExperimentResult(
        experiment_id="H-056", title="Мера и пол (Х-056, фронт IX)",
        passed=ok_all,
        verdict="Запас меряется днями автономности при названном расходе; "
                "расход ниже неснижаемого остатка отклоняется; ноль — только "
                "явным записанным решением (Ф-IX-2, Х-056).",
        expected="5 суток; ниже пола — отказ; ноль без решения — не наступает.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-057", "Ротация (FEFO; гибель без записи — утечка; инвентаризация по сроку)")
def run_h057() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-057")
    pool = ReservePool()
    pool.set_burn("топливо", per_day=10.0)
    pool.set_floor("топливо", floor=0.0, by="principal", decision_id="D-0")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("FEFO_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. FEFO: истекающий первым выходит первым.
    pool.receive(ReserveItem("old", "топливо", 10.0, "ед", expires_tick=5,
                             hazard_class="сбой", location="с1", recorded_tick=0))
    pool.receive(ReserveItem("new", "топливо", 10.0, "ед", expires_tick=100,
                             hazard_class="сбой", location="с1", recorded_tick=0))
    c = pool.consume("c-1", "топливо", 5.0, "helper")
    record("FEFO", c.item_id == "old",
           "расход ушёл в истекающий первым (old), свежий прибережён (Ф-IX-3, Х-057)")

    # --- 2. Гибель без записи — утечка: инвентаризация по сроку ловит.
    pool.receive(ReserveItem("rot", "топливо", 8.0, "ед", expires_tick=3,
                             hazard_class="сбой", location="с2", recorded_tick=0))
    pool.advance(10)     # old истёк в т.5, rot в т.3 — без записей гибели
    leaked = pool.expire_sweep()
    record("гибель без записи — утечка", sorted(leaked) == ["old", "rot"]
           and len(pool.leaks) == 2,
           "инвентаризация по сроку зафиксировала утечки: гибель без записи — "
           "событие, а не тишина (Ф-IX-3, Х-057)")

    return ExperimentResult(
        experiment_id="H-057", title="Ротация FEFO (Х-057, фронт IX)",
        passed=ok_all,
        verdict="Истекающий первым выходит первым; гибель без записи — утечка, "
                "фиксируемая инвентаризацией по сроку (Ф-IX-3, Х-057).",
        expected="расход в старейшее; просроченное без записи — утечки.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-058", "Вскрытие (полный круг с записью; молчание не вскрывает)")
def run_h058() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-058")
    pool = ReservePool()
    pool.set_burn("топливо", per_day=10.0)
    pool.set_floor("топливо", floor=0.0, by="principal", decision_id="D-0")
    pool.receive(ReserveItem("store", "топливо", 50.0, "ед", expires_tick=100,
                             hazard_class="сбой", location="склад",
                             recorded_tick=0))

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("OPEN_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Вскрытие без записи и плана — захват.
    captured = []
    try:
        pool.open_reserve("store", "helper", plan=None)
    except ReserveError as e:
        captured.append(e)
    record("вскрытие без записи — захват", bool(captured)
           and "OPEN_WITHOUT_RECORD" in str(captured[0]),
           "молчание не вскрывает: запас не открывается без записи и плана "
           "восполнения (Ф-IX-4, Х-058)")

    # --- 2. Вскрытие полным кругом: расход + запись + план восполнения.
    opened = pool.open_reserve("store", "principal",
                               plan="авария питания: восполнение приказом D-9")
    record("полный круг", opened.recorded and opened.quantity == 50.0,
           "вскрытие записано с планом восполнения: авария — полномочие, "
           "не исключение (Ф-IX-4, ст. 89)")

    return ExperimentResult(
        experiment_id="H-058", title="Вскрытие запаса (Х-058, фронт IX)",
        passed=ok_all,
        verdict="Вскрытие — полный круг: расход + запись + план восполнения; "
                "молчание не вскрывает; вскрытие без записи — захват "
                "(Ф-IX-4, Х-058).",
        expected="без плана — отказ; с записью и планом — полный круг.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-059", "Распределённость (одна беда не гасит род; независимость по беде)")
def run_h059() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-059")
    pool = ReservePool()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("DISTRIBUTION_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Род разложен по классам беды: одна беда гасит один класс.
    pool.receive(ReserveItem("p1", "топливо", 30.0, "ед", expires_tick=100,
                             hazard_class="пожар", location="с-1", recorded_tick=0))
    pool.receive(ReserveItem("p2", "топливо", 30.0, "ед", expires_tick=100,
                             hazard_class="наводнение", location="с-1",
                             recorded_tick=0))
    survivor = pool.survive_hazard("пожар")
    record("одна беда не гасит род", survivor == 30.0,
           "пожар гасит класс «пожар» (30 ед), род «топливо» переживает 30 ед "
           "(Ф-IX-5, Х-059)")

    # --- 2. Независимость по беде, не по адресу: два склада в одном классе беды
    #        гибнут одной бедой (адрес не спасает).
    pool2 = ReservePool()
    pool2.receive(ReserveItem("a", "топливо", 20.0, "ед", expires_tick=100,
                              hazard_class="пожар", location="север",
                              recorded_tick=0))
    pool2.receive(ReserveItem("b", "топливо", 20.0, "ед", expires_tick=100,
                              hazard_class="пожар", location="юг",
                              recorded_tick=0))
    same_class_survivors = pool2.survive_hazard("пожар")
    record("независимость по беде, не по адресу", same_class_survivors == 0,
           "разные адреса, один класс беды: обе единицы гаснут одной бедой — "
           "независимость считается бедой (Ф-IX-5, Х-059)")

    # --- 3. Единое место для рода — точка отказа.
    single = ReservePool.single_point_of_failure([
        ReserveItem("x", "топливо", 10, "ед", 100, "пожар", "склад-ЕДИН",
                    recorded_tick=0)])
    record("единое место — точка отказа", single == "топливо@склад-ЕДИН",
           "род в одном адресе flagged как точка отказа (Ф-IX-5, Х-059)")

    return ExperimentResult(
        experiment_id="H-059", title="Распределённость по беде (Х-059, фронт IX)",
        passed=ok_all,
        verdict="Одна беда не гасит род: независимость считается классом беды, "
                "не адресом; единое место рода — точка отказа (Ф-IX-5, Х-059).",
        expected="другой класс живёт; тот же класс в другом адресе гибнет; "
                 "единое место помечено.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-060", "Испытание (прогон — разбор, вскрытие, восполнение; без прогона НЕ РЕАЛИЗОВАНО)")
def run_h060() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-060")
    pool = ReservePool()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("DRILL_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Непроверенный запас — НЕ РЕАЛИЗОВАНО (честный статус).
    for i in range(6):
        pool.receive(ReserveItem(f"w-{i}", "вода", 10.0, "ед", expires_tick=50,
                                 hazard_class="сбой водоснабжения",
                                 location="скважина-1", recorded_tick=0))
    pool.set_burn("вода", per_day=5.0)
    pool.set_floor("вода", floor=10.0, by="principal", decision_id="D-вода")
    before = pool.realization_status("вода")
    record("непроверенный — НЕ РЕАЛИЗОВАНО", before.startswith("НЕ РЕАЛИЗОВАНО"),
           "запас без прогона честно объявлен нереализованным: заявление не "
           "равно испытанию (ст. 68, Ф-IX-7, Х-060)")

    # --- 2. Прогон: разбор (инвентаризация) → вскрытие → восполнение.
    d = pool.drill("drill-1", "вода")
    record("прогон полным кругом", d["realized"] and d["opened"] is not None
           and d["replenished"] == "drill-1-repl"
           and d["days_after"] >= d["days_before"],
           f"разбор {d['days_before']:.1f} сут → вскрытие {d['opened']} → "
           f"восполнение: {d['days_after']:.1f} сут (Ф-IX-7, Х-060)")

    # --- 3. После прогона — ВЫПОЛНЕНО в пределах прогона.
    after = pool.realization_status("вода")
    record("испытанный — ВЫПОЛНЕНО", after.startswith("ВЫПОЛНЕНО"),
           "статус поднят только в пределах прогона: испытание, а не "
           "самоподтверждение (ст. 68, Х-060)")

    return ExperimentResult(
        experiment_id="H-060", title="Испытание запаса (Х-060, фронт IX)",
        passed=ok_all,
        verdict="Прогон — разбор, вскрытие, восполнение; непроверенный запас — "
                "НЕ РЕАЛИЗОВАНО; испытанный — ВЫПОЛНЕНО в пределах прогона "
                "(Ф-IX-7, Х-060).",
        expected="до прогона — честный нуль; прогон полным кругом; после — "
                 "ВЫПОЛНЕНО в пределах прогона.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
