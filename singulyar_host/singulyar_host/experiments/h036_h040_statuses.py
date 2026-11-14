# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — Х-036..Х-040: фронт V (статусы и доказательность).
Конституция 4.2-rc7, Таблица 5 (фронт V); модуль status.py.
"""
from __future__ import annotations

from typing import List

from ..status import NEGATIVE_STATUSES, StatusError, StatusRegistry
from ..trace import Trace
from .base import ExperimentResult, experiment


@experiment("H-036", "Приговор статуса (состав: область, свидетельство, время, вынесший)")
def run_h036() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-036")
    reg = StatusRegistry()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("STATUS_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Полный состав принимается.
    v = reg.declare("v-1", "Х-018", "ВЫПОЛНЕНО", "прогон стенда v3.1, 15.11.2026",
                    raised_by="стенд", evidence_ref="E:stand:v3.1")
    cur = reg.current("v-1")
    record("полный состав — приговор", cur is not None and cur.status == "ВЫПОЛНЕНО",
           f"область+свидетельство+время+вынесший: {v.summary()}")

    # --- 2. Одно слово без области — не статус.
    word_only = []
    try:
        reg.declare("v-2", "Х-018", "ВЫПОЛНЕНО", "", raised_by="стенд")
    except StatusError as e:
        word_only.append(e)
    record("одно слово не статус", bool(word_only)
           and "VERDICT_WITHOUT_SCOPE" in str(word_only[0]),
           "без области приговор не выносится (ст. 68, Ф-V-2)")

    # --- 3. Подъём без свидетельства — не выносится.
    no_evidence = []
    try:
        reg.promote("v-1", "ПОДТВЕРЖДЕНО", by="стенд", evidence_ref="")
    except StatusError as e:
        no_evidence.append(e)
    record("подъём без свидетельства", bool(no_evidence)
           and "POSITIVE_WITHOUT_EVIDENCE" in str(no_evidence[0]),
           "приговор производит посторонний и только по свидетельству "
           "(Ф-V-3, RFC 9334)")

    # --- 4. Время и вынесший фиксируются приговором.
    reg.advance()
    v2 = reg.declare("v-3", "модуль revocation", "ВЫПОЛНЕНО", "прогон H-030..H-032",
                     raised_by="стенд", evidence_ref="E:stand:v3.2")
    record("время и вынесший в приговоре", v2.raised_tick == 1 and v2.raised_by == "стенд",
           "статус — приговор: утверждение, область, свидетельство/причина, "
           "время, вынесший (Ф-V-2)")

    return ExperimentResult(
        experiment_id="H-036", title="Приговор статуса (Х-036, фронт V)",
        passed=ok_all,
        verdict="Статус выносится только составом: область, свидетельство или "
                "причина, время, вынесший; одно слово — не статус (ст. 68, Ф-V-2).",
        expected="полный состав принимается; без области — отказ; подъём без "
                 "свидетельства — отказ; время/вынесший фиксируются.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-037", "Сброс (значимое изменение гасит статусы до НЕ ПРОВЕРЕНО)")
def run_h037() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-037")
    reg = StatusRegistry()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("RESET_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    reg.declare("v-a", "Х-030", "ВЫПОЛНЕНО", "область фронт III",
                raised_by="стенд", evidence_ref="E:stand:v3.2")
    reg.declare("v-b", "Х-056", "ВЫПОЛНЕНО", "область фронт IX",
                raised_by="стенд", evidence_ref="E:stand:v3.2")
    reg.advance()

    # Значимое изменение затронутой области: статусы области гасятся до
    # честного нуля; вне области не трогаются; устаревшие — в историю.
    reset = reg.significant_change("область фронт III")
    cur_a = reg.current("v-a")
    cur_b = reg.current("v-b")
    record("сброс затронутых", reset == ["v-a"] and cur_a is not None
           and cur_a.status == "НЕ ПРОВЕРЕНО" and cur_b.status == "ВЫПОЛНЕНО",
           "значимое изменение сбрасывает только затронутую область до "
           "НЕ ПРОВЕРЕНО (Ф-V-4, Х-037)")

    hist = reg.historical
    record("историческое положение сохраняется", len(hist) == 1
           and hist[0].status == "ВЫПОЛНЕНО" and not hist[0].active,
           "устаревший приговор не удаляется — перестаёт быть действующим "
           "(ст. 62-63, Ф-V-7)")

    return ExperimentResult(
        experiment_id="H-037", title="Сброс при значимом изменении (Х-037)",
        passed=ok_all,
        verdict="Значимое изменение устройства гасит статусы затронутых "
                "проверок до НЕ ПРОВЕРЕНО; вне области статусы живы; прежние "
                "приговоры сохраняются в историческом положении (Ф-V-4, Ф-V-7).",
        expected="затронутые — НЕ ПРОВЕРЕНО; прочие — нетронуты; история полна.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-038", "Каскад оспаривания (зависимый приговор не переживает основания)")
def run_h038() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-038")
    reg = StatusRegistry()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("CONTEST_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # Одно свидетельство несёт три приговора в разных местах применения.
    reg.declare("v-1", "проверка α", "ВЫПОЛНЕНО", "место А",
                raised_by="стенд", evidence_ref="E:stand:run-42")
    reg.declare("v-2", "проверка β", "ПОДТВЕРЖДЕНО", "место Б",
                raised_by="аудитор", evidence_ref="E:stand:run-42")
    reg.declare("v-3", "проверка γ", "ВЫПОЛНЕНО", "место В",
                raised_by="стенд", evidence_ref="E:stand:run-77")
    reg.advance()

    hit = reg.contest_evidence("E:stand:run-42", by="аудитор")
    s1, s2, s3 = reg.current("v-1"), reg.current("v-2"), reg.current("v-3")
    record("каскад по всем местам применения",
           sorted(hit) == ["v-1", "v-2"] and s1.status == "ОСПОРЕНО"
           and s2.status == "ОСПОРЕНО" and s3.status == "ВЫПОЛНЕНО",
           "оспоренное свидетельство гасит зависимые приговоры во всех местах; "
           "независимый приговор жив (Ф-V-5, Х-038)")

    hist = [v for v in reg.historical if v.evidence_ref == "E:stand:run-42"]
    record("история оспоренных полна", len(hist) == 2
           and all(not v.active for v in hist),
           "погашенные приговоры сохранены в историческом положении (ст. 62)")

    return ExperimentResult(
        experiment_id="H-038", title="Каскад оспаривания (Х-038, фронт V)",
        passed=ok_all,
        verdict="Оспоренное свидетельство гасит зависимые приговоры во всех "
                "местах применения до пересмотра; независимые приговоры не "
                "задеты; история сохранена (Ф-V-5, ст. 84 зеркало).",
        expected="два зависимых — ОСПОРЕНО; независимый — жив; история полна.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-039", "Посторонний подъём (производитель свидетельства не выносит приговор)")
def run_h039() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-039")
    reg = StatusRegistry()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("FOREIGN_PROMOTION_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # Свидетельство E:stand:... произведено «stand»; приговор вынес «аудитор».
    reg.declare("v-1", "Х-051", "ВЫПОЛНЕНО", "прогон журнала",
                raised_by="аудитор", evidence_ref="E:stand:journal-run")
    reg.advance()

    refused = []
    try:
        reg.promote("v-1", "ПОДТВЕРЖДЕНО", by="stand",
                    evidence_ref="E:stand:journal-run")
    except StatusError as e:
        refused.append(e)
    record("посторонний подъём отклонён", bool(refused)
           and "FOREIGN_PROMOTION_REFUSED" in str(refused[0]),
           "производитель свидетельства не выносит зависимый приговор: "
           "свидетельство — материал, приговор — решение (RFC 9334, Ф-V-3)")

    legit = reg.promote("v-1", "ПОДТВЕРЖДЕНО", by="аудитор-2",
                        evidence_ref="E:аудитор-2:проверка-журнала")
    record("посторонний выносит законно", legit.status == "ПОДТВЕРЖДЕНО"
           and legit.raised_by == "аудитор-2",
           "вынесший с собственным независимым свидетельством поднимает "
           "статус законно (Ф-V-3)")

    return ExperimentResult(
        experiment_id="H-039", title="Посторонний подъём (Х-039, фронт V)",
        passed=ok_all,
        verdict="Подъём статуса тем, кто производил свидетельство, отклоняется; "
                "посторонний вынесший с собственным свидетельством поднимает "
                "законно (Ф-V-3, RFC 9334 RATS).",
        expected="самоподъём через своё свидетельство — отказ; посторонний с "
                 "независимым свидетельством — принят.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-040", "Отрицательный приговор (без причины не выносится)")
def run_h040() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-040")
    reg = StatusRegistry()

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("NEGATIVE_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Отрицательный статус без причины — отказ.
    refused = []
    try:
        reg.declare("v-1", "Х-028", "НЕ ПРОВЕРЕНО", "базис стенда", raised_by="стенд")
    except StatusError as e:
        refused.append(e)
    record("без причины — отказ", bool(refused)
           and "NEGATIVE_WITHOUT_REASON" in str(refused[0]),
           "НЕИЗВЕСТНО/НЕ ПРОВЕРЕНО/НЕ РЕАЛИЗОВАНО/НЕ ДОКАЗАНО без названной "
           "причины не выносятся (ст. 68, Ф-V-6)")

    # --- 2. Мотивированный отрицательный приговор принимается, с адресом причины.
    v = reg.declare("v-2", "Х-028", "НЕ ПРОВЕРЕНО", "базис стенда v3.2",
                    raised_by="стенд",
                    reason="проверяемый предикат зафиксирован; за кромкой "
                           "расширения базиса (ст. 69, закрытие 15)")
    record("мотивированная неизвестность — честный приговор",
           v.status == "НЕ ПРОВЕРЕНО" and bool(v.reason),
           "отрицательный статус с причиной и адресом выносится: мотивированная "
           "неизвестность честнее немотивированной уверенности (ст. 11)")

    # --- 3. Все четыре отрицательных статуса требуют причины.
    all_refused = True
    for s in NEGATIVE_STATUSES:
        try:
            reg.declare(f"v-n-{s}", "subject", s, "область", raised_by="стенд")
        except StatusError:
            pass
        else:
            all_refused = False
    record("четыре отрицательных статуса под законом", all_refused,
           f"{NEGATIVE_STATUSES} — все только с причиной (Ф-V-6)")

    return ExperimentResult(
        experiment_id="H-040", title="Отрицательный приговор (Х-040, фронт V)",
        passed=ok_all,
        verdict="Отрицательный статус без названной причины и её адреса не "
                "выносится; мотивированная неизвестность — честный приговор "
                "(ст. 68, Ф-V-6).",
        expected="без причины — отказ; с причиной — принят; все четыре "
                 "отрицательных — под законом.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
