# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — Х-046..Х-050: фронт VII (минимальность).
Конституция 4.2-rc7, Таблица 5 (фронт VII); модуль minimality.py.
"""
from __future__ import annotations

from typing import List

from ..minimality import MinimalityError, MinimalityLedger
from ..trace import Trace
from .base import ExperimentResult, experiment


@experiment("H-046", "Мера (M(x) с областью; «минимально» без таблицы — не приговор)")
def run_h046() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-046")
    led = MinimalityLedger()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("MEASURE_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Элемент с мерой и областью вливается.
    el = led.admit("e-1", "статья 54", mx=3.5, scope="фронт III",
                   removal_predicate="опыт удаления: изъятие ст. 54 ломает "
                                     "Х-030..Х-032")
    record("мера с областью", el.mx == 3.5 and el.scope == "фронт III",
           "каждый элемент несёт M(x) и область (Ф-VII-2, Х-046)")

    # --- 2. «Минимально» без меры/области — не приговор.
    no_measure = []
    try:
        led.admit("e-2", "правило", mx=None, scope="область",
                  removal_predicate="предикат")
    except MinimalityError as e:
        no_measure.append(e)
    no_scope = []
    try:
        led.admit("e-3", "правило", mx=1.0, scope="",
                  removal_predicate="предикат")
    except MinimalityError as e:
        no_scope.append(e)
    record("без меры/области — не приговор", bool(no_measure) and bool(no_scope),
           "«минимально» без области и таблицы M(x) не выносится "
           "(Ф-VII-2, Х-046)")

    # --- 3. Сводная мера считается по элементам с областью.
    led.admit("e-4", "статья 55", mx=2.0, scope="фронт III",
              removal_predicate="изъятие ломает Х-031")
    record("сводная мера", abs(led.total() - 5.5) < 1e-9,
           "таблица M(x) суммируется по действующим элементам: "
           f"M(свода фронт III) = {led.total()}")

    return ExperimentResult(
        experiment_id="H-046", title="Мера M(x) (Х-046, фронт VII)",
        passed=ok_all,
        verdict="Каждый элемент несёт M(x) с областью; «минимально» без меры и "
                "области не приговор (Ф-VII-2, Х-046).",
        expected="с мерой — вливается; без меры/области — отказ; свод "
                 "считается по таблице.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-047", "Судьба нуля (сведение/удаление по порядку; дубли сливаются)")
def run_h047() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-047")
    led = MinimalityLedger()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("ZERO_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    led.admit("e-orig", "статья 54", mx=3.5, scope="фронт III",
              removal_predicate="опыт удаления")
    led.admit("e-dup", "статья 54", mx=3.5, scope="фронт III",
              removal_predicate="опыт удаления")     # дубль
    led.admit("e-zero", "выводимость способностей", mx=0.0, scope="закрытие 11",
              removal_predicate="решение: не является требованием (закрытие 11)")
    led.advance()

    report = led.sweep_zero()
    dup = led.element("e-dup")
    zero = led.element("e-zero")
    orig = led.element("e-orig")
    record("дубль сливается в первоисточник", dup.merged_into == "e-orig"
           and report["e-dup"].startswith("СЛИТ"),
           "дубли сливаются: остаётся первоисточник, дубль — ссылка (Ф-VII-3)")
    record("M=0 — судьба", zero.merged_into == ""
           and report["e-zero"].startswith("УДАЛЁН"),
           "M = 0 — не позор: элемент сведён или удалён по порядку, "
           "с записью (Ф-VII-3, Х-047)")
    record("первоисточник жив", orig.merged_into is None,
           "при слиянии и удалении первоисточник не тронут (ст. 62)")

    return ExperimentResult(
        experiment_id="H-047", title="Судьба нуля (Х-047, фронт VII)",
        passed=ok_all,
        verdict="M = 0 получает судьбу — сведение или удаление по порядку; "
                "дубли сливаются в первоисточник (Ф-VII-3, Х-047).",
        expected="дубль — ссылка; ноль — удалён по порядку; первоисточник — "
                 "жив.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-048", "Бремя добавления (норма без предиката удаления не вливается)")
def run_h048() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-048")
    led = MinimalityLedger()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("BURDEN_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    refused = []
    try:
        led.admit("e-1", "норма без выхода", mx=1.0, scope="область",
                  removal_predicate="")
    except MinimalityError as e:
        refused.append(e)
    record("без предиката удаления — не вливается", bool(refused)
           and "NO_REMOVAL_PREDICATE" in str(refused[0]),
           "добавление платит бременем: норма обязана предъявить, каким опытом "
           "она удаляется (Ф-VII-4, Х-048)")

    ok_el = led.admit("e-2", "норма с выходом", mx=1.0, scope="область",
                      removal_predicate="изъятие по опыту Х-048: замещается "
                                         "сведением к ст. 16")
    record("с предикатом — вливается", ok_el.removal_predicate is not None,
           "норма с честным предикатом удаления проходит бремя добавления")

    return ExperimentResult(
        experiment_id="H-048", title="Бремя добавления (Х-048, фронт VII)",
        passed=ok_all,
        verdict="Норма без предиката удаления не вливается: добавление платит "
                "бременем опыта своего удаления (Ф-VII-4, Х-048).",
        expected="без предиката — отказ; с предикатом — принят.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-049", "Ревизия свода (правило без применения и проверки — на пересмотр)")
def run_h049() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-049")
    led = MinimalityLedger(revision_period=10)

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("REVISION_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    led.admit("e-used", "статья 54", mx=3.5, scope="фронт III",
              removal_predicate="опыт удаления")
    led.admit("e-tested", "статья 55", mx=2.0, scope="фронт III",
              removal_predicate="опыт удаления")
    led.admit("e-stale", "мертвое правило", mx=1.0, scope="фронт III",
              removal_predicate="опыт удаления")
    led.advance(15)
    led.use("e-used")
    led.test("e-tested")
    stale = led.revise()
    record("мертвое — на пересмотр", "e-stale" in stale
           and "e-used" not in stale and "e-tested" not in stale,
           "правило без применения И без проверки за срок идёт на пересмотр: "
           "свод не самоочищается — его ревизируют (Ф-VII-5, Х-049)")

    return ExperimentResult(
        experiment_id="H-049", title="Ревизия свода (Х-049, фронт VII)",
        passed=ok_all,
        verdict="Правило без применения и проверки за срок назначенного — на "
                "пересмотр; применённое или проверенное живо (Ф-VII-5, Х-049).",
        expected="применённое/проверенное — живы; мёртвое — пересмотр.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-050", "Пересчёт (значимое изменение пересчитывает M(x))")
def run_h050() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-050")
    led = MinimalityLedger()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("RECOUNT_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    el = led.admit("e-1", "статья 54", mx=3.5, scope="фронт III",
                   removal_predicate="опыт удаления")
    led.advance()
    led.recount("e-1", 4.5, by="фронт III")
    hist = led.historical_log()
    record("пересчёт с историей", el.mx == 4.5 and len(el.historical_mx) == 1
           and el.historical_mx[0] == (1, 3.5) and bool(hist),
           "значимое изменение пересчитывает M(x); прежний приговор сохранён в "
           "историческом положении, не удалён (Ф-VII-6, Х-050)")

    return ExperimentResult(
        experiment_id="H-050", title="Пересчёт M(x) (Х-050, фронт VII)",
        passed=ok_all,
        verdict="Значимое изменение пересчитывает M(x); устаревший приговор "
                "уходит в историческое положение (Ф-VII-6, Х-050).",
        expected="мера обновлена; прежний приговор сохранён в истории.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
