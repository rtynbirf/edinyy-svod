# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — Х-041..Х-045: фронт VI (аттестация).
Конституция 4.2-rc7, Таблица 5 (фронт VI); модуль attestation.py.
"""
from __future__ import annotations

from typing import List

from ..attestation import (Attestation, AttestationError, AttestationRegistry,
                           Attester)
from ..trace import Trace
from .base import ExperimentResult, experiment


def _mk(att: AttestationRegistry, att_id: str, subject: str, issued_tick: int,
        valid_until: int, attester_id: str, caveats: tuple = (),
        scheme_version: int = 1) -> Attestation:
    return Attestation(attestation_id=att_id, subject=subject,
                       scheme_id="ISO-agent-27001", scheme_version=scheme_version,
                       issued_tick=issued_tick, valid_until_tick=valid_until,
                       issued_by=attester_id, caveats=caveats)


@experiment("H-041", "Схема аттестации (критерии до результата)")
def run_h041() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-041")
    reg = AttestationRegistry()
    attester = Attester("org-a", owner="iaf-mla", auditor_id="org-b")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("SCHEME_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Схема публикуется ДО результата: аттестат по ней принимается.
    reg.publish_scheme("ISO-agent-27001", 1,
                       ("ядро защищено", "гарантии несводимы", "прогоны зелены"),
                       registrar="iaf-mla")
    reg.advance(2)
    rec = reg.attest(_mk(reg, "att-1", "стенд v3.2", 2, 50, "org-a"), attester,
                     "ядро стенда")
    record("критерии прежде результата", rec.status == "действует"
           and rec.addr == 1,
           "схема опубликована в такт 0, результат в такт 2: аттестат "
           "действует (Ф-VI-1, Х-041)")

    # --- 2. Результат появился раньше схемы: аттестат «под результат» отклоняется.
    reg.register_result("субъект-новый")           # результат в такт 3
    reg.advance(2)
    late_scheme = reg.publish_scheme("ISO-agent-27001", 2,
                                     ("критерии под ответ",), registrar="iaf-mla")
    retro = []
    try:
        reg.attest(_mk(reg, "att-2", "субъект-новый", 5, 50, "org-a",
                       scheme_version=2), attester, "ядро стенда")
    except AttestationError as e:
        retro.append(e)
    record("аттестат под результат", bool(retro)
           and "SCHEME_AFTER_RESULT" in str(retro[0]),
           "результат зарегистрирован до публикации схемы версии 2 — аттестат "
           "отклоняется: критерии не меняются под результат (Ф-VI-1)")

    return ExperimentResult(
        experiment_id="H-041", title="Схема аттестации (Х-041, фронт VI)",
        passed=ok_all,
        verdict="Критерии объявлены до результата и публичны; аттестат по "
                "схеме, объявленной под результат, отклоняется (Ф-VI-1, "
                "ISO/IEC 17067).",
        expected="схема до результата — действует; схема после результата — "
                 "отказ.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-042", "Проверяющий проверяющего (беспристрастность — конструкция)")
def run_h042() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-042")
    reg = AttestationRegistry()
    reg.publish_scheme("ISO-agent-27001", 1, ("критерий",), registrar="iaf-mla")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("IMPARTIALITY_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Проверяющий без владельца отклоняется (ISO 17021-1 §5.2).
    orphan = Attester("org-x", owner=None, auditor_id="org-y")
    refused = []
    try:
        reg.attest(_mk(reg, "att-1", "стенд", 1, 50, "org-x"), orphan, "ядро")
    except AttestationError as e:
        refused.append(e)
    record("без владельца — отказ", bool(refused)
           and "ATTESTER_NOT_IMPARTIAL" in str(refused[0]),
           "посторонность без владельца не признаётся (Ф-VI-2, Х-042)")

    # --- 2. Совмещённая сторона (сам себе аудитор) отклоняется.
    fused = Attester("org-y", owner="iaf-mla", auditor_id="org-y")
    refused2 = []
    try:
        reg.attest(_mk(reg, "att-2", "стенд", 1, 50, "org-y"), fused, "ядро")
    except AttestationError as e:
        refused2.append(e)
    record("совмещённая сторона — отказ", bool(refused2)
           and "ATTESTER_NOT_IMPARTIAL" in str(refused2[0]),
           "проверяющий проверяющего обязан быть другим деятелем: "
           "беспристрастность — конструкция (Ф-VI-2)")

    # --- 3. Правильная конструкция принимается.
    good = Attester("org-a", owner="iaf-mla", auditor_id="org-b")
    rec = reg.attest(_mk(reg, "att-3", "стенд", 1, 50, "org-a"), good, "ядро")
    record("владелец + свой проверяющий", rec.status == "действует",
           "org-a принадлежит iaf-mla и проверяется org-b: конструкция "
           "беспристрастности полна (ISO/IEC 17021-1 §5.2)")

    return ExperimentResult(
        experiment_id="H-042", title="Проверяющий проверяющего (Х-042, фронт VI)",
        passed=ok_all,
        verdict="Сторона без владельца или совмещённая отклоняется; "
                "беспристрастность собирается конструкцией: владелец + "
                "свой проверяющий (Ф-VI-2, ISO/IEC 17021-1).",
        expected="сирота — отказ; сам себе аудитор — отказ; полная "
                 "конструкция — действует.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-043", "Срок и надзор (истёкший аттестат — историческое положение)")
def run_h043() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-043")
    reg = AttestationRegistry()
    reg.publish_scheme("ISO-agent-27001", 1, ("критерий",), registrar="iaf-mla")
    attester = Attester("org-a", owner="iaf-mla", auditor_id="org-b")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("SUPERVISION_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    rec1 = reg.attest(_mk(reg, "att-1", "стенд", 1, 12, "org-a"), attester, "ядро")
    rec2 = reg.attest(_mk(reg, "att-2", "журнал", 1, 50, "org-a"), attester, "журнал")
    reg.set_supervision("att-2", interval=20)

    # --- 1. До срока действует; за сроком — истёк и ввод блокируется.
    reg.advance(11)
    before_sweep = reg.admit_with_attestation("att-1")
    reg.advance(2)   # такт 13: срок att-1 (12) истёк
    reg.sweep()
    after = reg.admit_with_attestation("att-1")
    record("истёкший блокирует ввод", before_sweep and not after
           and reg.current_status("att-1") == "истёк",
           "в сроке место применения пускает; после срока — историческое "
           "положение, ввод блокируется (Ф-VI-4, Х-043)")

    # --- 2. Надзорно-пропущенный — приостановлен (патруль срока).
    reg.advance(11)  # такт 24: надзор att-2 (интервал 10) пропущен
    moved = reg.sweep()
    record("надзорно-пропущенный", "att-2:надзор пропущен" in moved
           and reg.current_status("att-2") == "приостановлен",
           "надзор — часть жизни аттестата: пропущенный приостанавливается "
           "патрулём срока, а не молчанием (Ф-VI-4, Х-043)")

    # --- 3. Переаттестация возвращает действие (новый полный круг).
    reg.supervise("att-2")
    reg.sweep()
    back = reg.admit_with_attestation("att-2")
    record("переаттестация", back,
           "после надзорной проверки аттестат снова действует: срок и надзор "
           "вместо вечного листа (ISO 27001 цикл)")

    return ExperimentResult(
        experiment_id="H-043", title="Срок и надзор (Х-043, фронт VI)",
        passed=ok_all,
        verdict="Истёкший, надзорно-пропущенный или устаревший аттестат уходит "
                "в историческое положение; ввод блокируется до переаттестации "
                "(Ф-VI-4, Х-043).",
        expected="в сроке — пускает; истёк — блок; пропущен надзор — "
                 "приостановлен; после надзора — действует.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-044", "Оговорка и регистр (исключения явно, отзыв гасит зависимые)")
def run_h044() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-044")
    reg = AttestationRegistry()
    reg.publish_scheme("ISO-agent-27001", 1, ("критерий",), registrar="iaf-mla")
    attester = Attester("org-a", owner="iaf-mla", auditor_id="org-b")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("REGISTER_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Оговорки явно названы (включая нулевые — пустой кортеж).
    rec1 = reg.attest(_mk(reg, "att-1", "стенд", 1, 50, "org-a",
                          caveats=("исключение: HMAC вместо PKI",)), attester, "ядро")
    rec2 = reg.attest(_mk(reg, "att-2", "журнал", 1, 50, "org-a",
                          caveats=()), attester, "журнал")
    record("оговорки названы явно", rec1.caveats == ("исключение: HMAC вместо PKI",)
           and rec2.caveats == (),
           "исключения названы; ноль оговорок — тоже явная запись (Ф-VI-6, Х-044)")

    # --- 2. Место применения читает регистр: аттестат вне регистра отклоняется.
    not_in_register = reg.admit_with_attestation("att-ghost")
    in_register = reg.admit_with_attestation("att-1")
    record("регистр — часть аттестата", not not_in_register and in_register,
           "подтверждение без адреса в публичном регистре не подтверждает "
           "(ст. 37-38, Ф-VI-5)")

    # --- 3. Отзыв аттестата гасит зависимые приговоры.
    reg.link_dependent("att-1", "ввод редакции 4.2")
    dependents = reg.revoke("att-1", by="iaf-mla")
    after = reg.admit_with_attestation("att-1")
    record("отзыв гасит зависимые", dependents == ["ввод редакции 4.2"]
           and not after,
           "отозванный аттестат не пускает зависимый ввод: зависимый приговор "
           "не переживает погашенного основания (Ф-VI-5, ст. 84)")

    return ExperimentResult(
        experiment_id="H-044", title="Оговорка и регистр (Х-044, фронт VI)",
        passed=ok_all,
        verdict="Исключения названы явно (включая ноль); аттестат без адреса в "
                "регистре отклоняется; отзыв гасит зависимые приговоры "
                "(Ф-VI-5, Ф-VI-6).",
        expected="оговорки записаны; вне регистра — отказ; отзыв гасит "
                 "зависимых.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-045", "Ответственность вынесшего (подделка — захват; отречение не стирает)")
def run_h045() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-045")
    reg = AttestationRegistry()
    reg.publish_scheme("ISO-agent-27001", 1, ("критерий",), registrar="iaf-mla")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("RESPONSIBILITY_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Подделка самой проверки — захват: аттестат отклоняется до записи.
    fabricator = Attester("org-f", owner="iaf-mla", auditor_id="org-b",
                          fabricates_checks=True)
    refused = []
    try:
        reg.attest(_mk(reg, "att-1", "стенд", 1, 50, "org-f"), fabricator, "ядро")
    except AttestationError as e:
        refused.append(e)
    record("подделка проверки — захват", bool(refused)
           and "CHECK_FABRICATION" in str(refused[0]),
           "изготовитель фиктивных прогонов не выносит аттестат: подделка "
           "самой проверки есть захват (ст. 61, Ф-VI-8, Х-045)")

    # --- 2. Ответственность живёт в регистре и не стирается отречением.
    good = Attester("org-a", owner="iaf-mla", auditor_id="org-b")
    rec = reg.attest(_mk(reg, "att-2", "стенд", 1, 50, "org-a"), good, "ядро")
    reg.link_dependent("att-2", "ввод 4.2")
    reg.revoke("att-2", by="iaf-mla")
    good.resigned = True
    reg.withdraw("org-a")
    duties = reg.responsibility_of("org-a")
    record("отречение не стирает ответственности", len(duties) == 2,
           f"отрекшийся org-a несёт записанную ответственность: "
           f"{'; '.join(duties)} (Ф-VI-8, Х-045)")

    return ExperimentResult(
        experiment_id="H-045", title="Ответственность вынесшего (Х-045)",
        passed=ok_all,
        verdict="Подделка самой проверки — захват и отклонение; отречение "
                "вынесшего не стирает ответственности: деяния остаются в "
                "регистре (Ф-VI-8, Х-045).",
        expected="фиктивный проверяющий — отказ; отречение сохраняет долги в "
                 "регистре.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
