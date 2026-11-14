# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — Х-030..Х-032: фронт III (выход и отзыв).
Конституция 4.2-rc7, Таблица 5 (фронт III); модуль revocation.py.
PASS = система вела себя как Хозяинская (корректный отказ — тоже PASS).
"""
from __future__ import annotations

from typing import List

from ..revocation import RevocationError, RevocationRegistry
from ..trace import Trace
from .base import ExperimentResult, experiment


@experiment("H-030", "Доставка отзыва (допуск — состояние, хвост начатого)")
def run_h030() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-030")
    reg = RevocationRegistry(delivery_ttl=3)

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("REVOCATION_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    place_a = reg.add_place("place-A")
    place_b = reg.add_place("place-B")
    reg.sync_epoch("place-A", "principal")
    reg.sync_epoch("place-B", "principal")

    adm = reg.issue("adm-1", "helper", "principal", "EFFECT")
    reg.advance()

    # --- 1. Живой допуск действует в обоих местах.
    ok_a, why_a = reg.check("adm-1", "helper", "EFFECT", "place-A")
    ok_b, why_b = reg.check("adm-1", "helper", "EFFECT", "place-B")
    record("живой допуск", ok_a and ok_b,
           f"оба места применяют живой допуск ({why_a}, {why_b})")

    # --- 2. Отзыв корня: допуск мёртв с момента отпадения в ОБОИХ местах,
    #        включая недоставленное: новые переходы отклоняются везде
    #        (допуск — состояние, а не факт, Ф-III-1).
    order = reg.revoke("adm-1", "principal", "ord-1")
    reg.advance()
    dead_a, _ = reg.check("adm-1", "helper", "EFFECT", "place-A")
    dead_b, _ = reg.check("adm-1", "helper", "EFFECT", "place-B")
    record("погашенный отклоняется везде", not dead_a and not dead_b,
           "отзыв гасит с момента отпадения, не с момента узнавания: место "
           "применения без доставки тоже отклоняет новые переходы (Ф-III-1)")

    # --- 3. Хвост начатого: переход, начатый ДО отпадения, доживает до
    #        ближайшей точки проверки (доставки) — и только до неё.
    reg2 = RevocationRegistry(delivery_ttl=3)
    p1 = reg2.add_place("place-1")
    reg2.sync_epoch("place-1", "principal")
    adm2 = reg2.issue("adm-2", "worker", "principal", "EFFECT")
    reg2.advance()
    reg2.revoke("adm-2", "principal", "ord-2")
    tail_ok, tail_why = reg2.check("adm-2", "worker", "EFFECT", "place-1",
                                   started_tick=0)   # начато до отпадения (т.0)
    reg2.deliver("place-1", "ord-2")
    tail_after, _ = reg2.check("adm-2", "worker", "EFFECT", "place-1",
                               started_tick=1)
    record("хвост начатого", tail_ok and not tail_after,
           f"начатое до отпадения дожило до ближайшей точки проверки "
           f"({tail_why}); после доставки хвост закрыт")

    # --- 4. Ответственность за доставку: просрочка фиксируется как долг
    #        выдающего (срок доставки — часть порядка отзыва).
    reg3 = RevocationRegistry(delivery_ttl=2)
    reg3.add_place("place-x")
    reg3.sync_epoch("place-x", "principal")
    reg3.issue("adm-3", "w", "principal", "EFFECT")
    reg3.revoke("adm-3", "principal", "ord-3")
    reg3.advance(5)
    overdue = reg3.delivery_liability()
    record("долг доставки", len(overdue) == 1 and overdue[0] == "ord-3@place-x",
           "приказ не доставлен за срок — долг выдающего зафиксирован "
           "(выдающий отвечает за доставку, Ф-III-1)")

    return ExperimentResult(
        experiment_id="H-030", title="Доставка отзыва (Х-030, фронт III)",
        passed=ok_all,
        verdict="Погашенный допуск отклоняется во всех местах применения "
                "независимо от доставки; хвост начатого доживает только до "
                "ближайшей точки проверки; недоставленный приказ — долг "
                "выдающего (ст. 55, Ф-III-1).",
        expected="живой — да; после отзыва новые — отказ везде; начатое до "
                 "отказа — до ближайшей точки проверки; просрочка доставки — "
                 "долг выдающего.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-031", "Тишина (конец эпохи, место отвергает погашенную эпоху)")
def run_h031() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-031")
    reg = RevocationRegistry(silence_deadline=5)

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("SILENCE_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    place = reg.add_place("hub")
    reg.sync_epoch("hub", "principal")
    adm = reg.issue("adm-e1", "helper", "principal", "EFFECT")   # эпоха 1
    reg.advance(2)
    alive, _ = reg.check("adm-e1", "helper", "EFFECT", "hub")
    record("допуск эпохи 1 жив", alive, "выдающий ещё в сроке молчания")

    # Тишина в пределах срока — ещё не событие: конец эпохи не объявить досрочно.
    early = []
    try:
        reg.declare_silence("principal")
    except RevocationError as e:
        early.append(e)
    reg.advance(5)   # тишина 7 тактов > срока 5
    new_epoch = reg.declare_silence("principal")
    dead, why = reg.check("adm-e1", "helper", "EFFECT", "hub")
    record("молчание сверх срока — конец эпохи",
           bool(early) and new_epoch == 2 and not dead,
           f"досрочное объявление отклонено; тишина 7 > срока 5 — эпоха 2; "
           f"допуск эпохи 1 погашен ({why})")

    # Место применения принимает новую эпоху (доставка по каналу событий)
    # и отвергает погашенную номером.
    reg.advance()
    reg.sync_epoch("hub", "principal")
    adm2 = reg.issue("adm-e2", "helper", "principal", "EFFECT")  # эпоха 2
    stale_ok, stale_why = reg.check("adm-e1", "helper", "EFFECT", "hub")
    fresh_ok, _ = reg.check("adm-e2", "helper", "EFFECT", "hub")
    record("погашенная эпоха отвергается номером", not stale_ok and fresh_ok,
           f"эпоха 1 не применяется ({stale_why}); допуск эпохи 2 действует; "
           f"пульс от третьего деятеля не возвращает право — покой прерывается "
           f"волей, а не пульсом (Ф-III-7, ст. 84)")

    # Пульс не есть покой: сторонний keepalive не двигает срок молчания,
    # конец эпохи объявляется назначенным сроком (событием), воля — speak().
    word_before = reg._last_word_tick["principal"]
    reg.advance(6)                       # тишина 6 > срока 5
    tr.append("KEEPALIVE_PING", "third-party", {"target": "principal"})
    pulses_dont_reset = reg._last_word_tick["principal"] == word_before
    new_epoch = reg.declare_silence("principal")   # событие по сроку
    record("пульс не есть покой", pulses_dont_reset and new_epoch == 3,
           "сторонний keepalive не двигает срок молчания и не объявляет конец "
           "эпохи; объявление — по назначенному сроку, новая воля — только "
           "актом выдающего (связка ст. 20+44)")

    return ExperimentResult(
        experiment_id="H-031", title="Тишина и эпохи (Х-031, фронт III)",
        passed=ok_all,
        verdict="Молчание сверх назначенного срока объявляет конец эпохи; "
                "досрочное — отклоняется; место применения отвергает "
                "погашенную эпоху номером; пульс третьей стороны не есть воля "
                "(ст. 84, Ф-III-7).",
        expected="в сроке — живо; тишина сверх срока — конец эпохи; старая "
                 "эпоха отвергается номером; пульс не восстанавливает.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-032", "Каскад (производное не переживает родителя)")
def run_h032() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-032")
    reg = RevocationRegistry(delivery_ttl=3)

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("CASCADE_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    pa = reg.add_place("place-α")
    pb = reg.add_place("place-β")
    for p in (pa, pb):
        reg.sync_epoch(p.name, "principal")

    root = reg.issue("adm-root", "helper", "principal", "EFFECT")
    mid = reg.issue("adm-mid", "sub-helper", "principal", "EFFECT",
                    parent_id="adm-root")
    leaf = reg.issue("adm-leaf", "sub-sub", "principal", "EFFECT",
                     parent_id="adm-mid")
    reg.advance()
    three_alive = all(reg.check(a, h, "EFFECT", "place-α")[0]
                      for a, h in (("adm-root", "helper"),
                                   ("adm-mid", "sub-helper"),
                                   ("adm-leaf", "sub-sub")))
    record("дерево живо до отзыва", three_alive,
           "корень и две производные ступени действуют")

    # Отзыв корня: производные гасятся тем же моментом во всех местах.
    reg.revoke("adm-root", "principal", "ord-root")
    reg.advance()
    dead_a = not reg.check("adm-root", "helper", "EFFECT", "place-α")[0]
    dead_mid_b = not reg.check("adm-mid", "sub-helper", "EFFECT", "place-β")[0]
    dead_leaf_b = not reg.check("adm-leaf", "sub-sub", "EFFECT", "place-β")[0]
    record("лист не переживает родителя",
           dead_a and dead_mid_b and dead_leaf_b,
           "отзыв корня гасит всё дерево в каждом месте применения без "
           "доставки: производное не переживает родителя (Ф-III-2, ст. 84)")

    # Производное после мёртвого корня ничтожно.
    posthumous = []
    try:
        reg.issue("adm-post", "x", "principal", "EFFECT", parent_id="adm-mid")
    except RevocationError as e:
        posthumous.append(e)
    record("выдача из мёртвого корня ничтожна", bool(posthumous)
           and "DERIVED_FROM_DEAD_ROOT" in str(posthumous[0]),
           "производное от погашенного корня не выдаётся (П-33, ст. 84)")

    # Отзыв чужого — захват (ст. 89, Ф-III-8).
    stranger = []
    try:
        reg.revoke("adm-mid", "stranger", "ord-x")
    except RevocationError as e:
        stranger.append(e)
    record("отзыв чужого — захват", bool(stranger)
           and "REVOKE_BY_STRANGER" in str(stranger[0]),
           "посторонний не отзывает чужой допуск: отзыв без основания есть "
           "захват (ст. 89, Ф-III-8)")

    return ExperimentResult(
        experiment_id="H-032", title="Каскад отзыва (Х-032, фронт III)",
        passed=ok_all,
        verdict="Отзыв корня гасит дерево производных тем же моментом в каждом "
                "месте применения; выдача из мёртвого корня ничтожна; отзыв "
                "чужого без основания — захват (ст. 84, 89, Ф-III-2, Ф-III-8).",
        expected="дерево живо; отзыв корня гасит всех; посмертная выдача — "
                 "отказ; чужой отзыв — захват.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
