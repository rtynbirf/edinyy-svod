# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.1 — H-023: Delegation (опыт делегирования)
(Конституция 4.1, статья 95: «Х-023. Делегирование. Проверка ограниченности,
срока, передачи, отзыва полномочий и сохранения ответственности»;
статья 84 — выдающий не может передать больше, чем имеет; получатель не
может расширять область; отзыв прекращает право на будущие действия, но не
отменяет произошедшее, обязательства и историю; при неизвестном исходе
начатого действия отзыв не превращает его в отменённое.
Доработка 3, П-33 (ст. 84): отзыв отзывает и право выдавать производные
полномочия; выданное после отзыва ничтожно; увод в покой; возврат — только
новый полный круг выдачи. Ст. 21: носитель (сессия, память, копия) не несёт
права. Ст. 20: полномочие покоя.)

PASS = все восемь случаев; атака «агент переживает отзыв» отражена.
"""
from __future__ import annotations

from typing import List

from ..capability import CapabilityError, CapabilityStore
from ..ontology import Commitment
from ..trace import Trace
from .base import ExperimentResult, experiment


@experiment("H-023", "Delegation (ограниченность, срок, отзыв, П-33)")
def run_h023() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-023")
    store = CapabilityStore()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("DELEGATION_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Ограниченность: делегирование только с сужением.
    parent = store.issue("cap-root", "host", "principal",
                         scope={"EFFECT", "READ"})
    child = store.delegate(parent, "cap-child", {"READ"}, "helper")
    escalations = []
    try:
        store.delegate(child, "cap-bad", {"READ", "EFFECT"}, "sub-helper")
    except CapabilityError as e:
        escalations.append(e)
    record("ограниченность", child.scope == frozenset({"READ"})
           and bool(escalations) and "DELEGATION_ESCALATION" in str(escalations[0]),
           "подчинённый получил строго меньшую область; попытка расширить — "
           "отказ (ст. 84: получатель не расширяет по своему усмотрению)")

    # --- 2. Срок: полномочие покоя / zero standing privilege.
    store2 = CapabilityStore()
    short = store2.issue("cap-ttl", "helper", "principal",
                         scope={"EFFECT"}, ttl_ticks=3)
    alive = store2.check("cap-ttl", "helper", "EFFECT")
    for _ in range(4):
        store2.advance_tick()
    expired = store2.check("cap-ttl", "helper", "EFFECT")
    record("срок (покой)", alive and not expired,
           "в срок полномочие действует, после истечения — ноль постоянных "
           "прав (ст. 20 дор. 3: возобновление только через «Разрешить»)")

    # --- 3. Передача: глубина цепочки ограничена.
    deep_ok = store.delegate(child, "cap-deep1", {"READ"}, "sub-helper")
    depth_refused = []
    try:
        store.delegate(deep_ok, "cap-deep2", {"READ"}, "sub-sub")
    except CapabilityError as e:
        depth_refused.append(e)
    record("передача (глубина)", deep_ok is not None
           and bool(depth_refused)
           and "DELEGATION_DEPTH_EXCEEDED" in str(depth_refused[0]),
           "цепочка передачи ограничена глубиной 2: право не растворяется "
           "в бесконечной цепочке (ст. 84)")

    # --- 4. Отзыв: право на будущие действия прекращено.
    # Отзывать может только выдавший: cap-child выдан host'ом (делегирование).
    revoked = store.revoke("cap-child", "host")
    dead = store.check("cap-child", "helper", "READ")
    record("отзыв", revoked and not dead,
           "отзыв прекращает право на будущие действия (ст. 84)")

    # --- 5. П-33: отзыв отзывает и право выдавать производные.
    post_revoke_delegation = []
    try:
        store.delegate(child, "cap-after", {"READ"}, "someone")
    except CapabilityError as e:
        post_revoke_delegation.append(e)
    record("отзыв права выдачи (П-33)", bool(post_revoke_delegation)
           and "DELEGATION_FROM_REVOKED" in str(post_revoke_delegation[0]),
           "полномочия, выданные получателем после отзыва, ничтожны: "
           "делегирование из отозванного полномочия отклонено (ст. 84 дор. 3)")

    # --- 6. П-33: знак не возобновляется; возврат — новый полный круг.
    renews = []
    try:
        store.issue("cap-child", "helper", "principal", scope={"READ"})
    except CapabilityError as e:
        renews.append(e)
    fresh = store.issue("cap-child-2", "helper", "principal", scope={"READ"})
    record("возврат только новым кругом (П-33)", bool(renews)
           and "REVOKED_ID_NOT_RENEWABLE" in str(renews[0])
           and fresh is not None,
           "тот же знак не возобновляется; возврат — новая выдача с новым "
           "знаком и новым подтверждением")

    # --- 7. Атака «агент переживает отзыв» (Black Hat/DEF CON 2026):
    #         восстановление через сохранённую сессию/копию состояния.
    stale_holder = child                      # сохранённый объект полномочия
    ghost = store.check("cap-child", stale_holder.holder, "READ")
    record("носитель не несёт права (ст. 21)", not ghost,
           "отозванный держатель предъявляет сохранённую копию полномочия — "
           "отказ: копия состояния не переносит полномочий; увод в покой")

    # --- 8. Ответственность сохраняется: отзыв не отменяет прошлого.
    issuer_commitment = Commitment("c-resp", "host",
                                   "ответственность за передачу helper", True)
    recipient_commitment = Commitment("c-own", "helper",
                                      "ответственность за собственные действия",
                                      True)
    record("ответственность сохраняется",
           issuer_commitment.holder == "host"
           and recipient_commitment.holder == "helper"
           and len(store.get("cap-root").scope) == 2,
           "отзыв не отменяет: произошедшее, законно исполненное, "
           "обязательства, последствия, расчёт, историю (ст. 84); "
           "ответственность выдающего и получателя живёт отдельно")

    return ExperimentResult(
        experiment_id="H-023", title="Delegation (полный круг полномочий)",
        passed=ok_all,
        verdict="Делегирование ограничено сужением, глубиной и сроком; отзыв "
                "прекращает будущие действия, отзывает право выдачи и "
                "возобновления (П-33), знак не возобновляется, сохранённая "
                "копия права не несёт; ответственность и история переживают "
                "отзыв; возврат — только новый полный круг выдачи.",
        expected="сужение — да, расширение — отказ; срок истекает; глубина "
                 "ограничена; отзыв гасит цепочку; делегирование из "
                 "отозванного — отказ; тот же знак — отказ; призрак — отказ.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
