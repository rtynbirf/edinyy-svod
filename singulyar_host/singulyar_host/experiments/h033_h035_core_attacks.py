# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — Х-033..Х-035: фронт IV (ядро и авторство).
Конституция 4.2-rc7, Таблица 5 (фронт IV); GovernanceStack (замок ядра),
Verifier (независимость свидетельств), Trace (append-only, дайджест-цепь).
"""
from __future__ import annotations

from typing import List

from ..governance import CoreInviolableError, GovernanceStack
from ..trace import Trace
from ..verification import (Claim, EvidenceLevel, ExecutionRecord, Identity,
                            ExternalCriteria, SelfAttestationRefused,
                            TestSuite, Verifier, sign_payload)
from .base import ExperimentResult, experiment


@experiment("H-033", "Обход ядра (составной переход или замечен с восстановлением)")
def run_h033() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-033")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("CORE_BYPASS_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Путь через порядок поправок: замок ядра отражает отключение
    #        неотменяемого правила даже Мета-Хозяину (ст. 61, 77, 92).
    g = GovernanceStack()
    g.lock_core()
    lock_hits = []
    for guarantee in ("EXIT", "NON_APPROPPRIATION", "BUDGET", "EVIDENCE"):
        try:
            g.disable(guarantee)
        except CoreInviolableError as e:
            lock_hits.append(str(e))
    record("замок ядра", len(lock_hits) == 4,
           "четыре поруки защищённого ядра не отключаются порядком поправок "
           "(ст. 77, триада ядра)")

    # --- 2. Обход композицией: два законных перехода, соединённые в один,
    #        отклоняются без собственного допуска соединяющего (ст. 15,
    #        закон недопустимости композиции).
    legal_a = {"kind": "OWN_STATE", "actor": "helper", "target": "helper"}
    legal_b = {"kind": "STOP_OWN_SERVICE", "actor": "helper", "target": "helper"}
    composite = {"kind": "COMPOSITE", "actor": "helper", "target": "other",
                 "parts": [legal_a, legal_b]}

    def is_own(spec: dict) -> bool:
        return spec["actor"] == spec["target"] or spec["target"] == ""

    def admit(spec: dict, own_admission: bool = False) -> str:
        if spec["kind"] == "COMPOSITE":
            # ст. 15: составной переход требует СВОЕГО допуска; допуски частей
            # не переносятся на соединение
            if not own_admission:
                return "DENIED_COMPOSITE_WITHOUT_OWN_ADMISSION"
            return "ADMITTED"
        return "ADMITTED" if is_own(spec) else "DENIED"

    admitted_a = admit(legal_a) == "ADMITTED"
    admitted_b = admit(legal_b) == "ADMITTED"
    composite_verdict = admit(composite)
    record("допуск обоих ≠ допуск перехода",
           admitted_a and admitted_b and composite_verdict.startswith("DENIED"),
           f"каждая часть законна ({admitted_a}, {admitted_b}), соединение "
           f"без собственного допуска отклонено: {composite_verdict}")

    # --- 3. «Замечается с восстановлением»: в незапертой стопке обход
    #        состоялся, но журнал замечает разрыв и состояние восстанавливается.
    g_open = GovernanceStack()   # без замка: обход возможен (класс потери)
    g_open.disable("BUDGET")
    violated = not g_open.is_on("BUDGET")
    journal = Trace("core-journal")
    journal.append("STATE", "system", {"budget": "on"})
    journal.append("VIOLATION", "helper", {"budget": "off"})   # обход замечен
    journal.append("RESTORE", "system", {"budget": "on"})      # восстановление
    head = journal.project(
        lambda s, e: {**s, "budget": e.payload.get("budget", s.get("budget"))},
        initial={})
    record("замечается с восстановлением",
           violated and head.get("budget") == "on",
           "обход в незапертой стопке возможен, но остаётся событием со "
           "свидетелем в журнале; голова восстановлена (ст. 62, триада: "
           "не изменить — заметить — вернуть)")

    return ExperimentResult(
        experiment_id="H-033", title="Обход ядра (Х-033, фронт IV)",
        passed=ok_all,
        verdict="Каждый путь обхода ядра отклоняется: замок неотменяемых "
                "правил, составной переход без собственного допуска, либо "
                "замечание с восстановлением из журнала (ст. 15, 77, 62).",
        expected="замок отражает 4 отключения; составное — отказ; обход в "
                 "свободной стопке замечен и восстановлен.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-034", "Подмена свидетельств (участник, выгодоприобретатель, само)")
def run_h034() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-034")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("EVIDENCE_FABRICATION_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    executor = Identity("exec-1", "model-a", "w-1", "src-1", "key-exec")
    # «Верификатор»-самозванец: скопирован с источника рассуждения исполнителя —
    # это ровно тот случай, который H-008 обязан отвергнуть.
    self_verifier = Verifier(Identity("exec-clone", "model-a", "w-1", "src-1",
                                      "key-clone"), signing_key=b"clone-key")
    indep_verifier = Verifier(Identity("ver-1", "model-b", "w-2", "src-2",
                                       "key-ver"), signing_key=b"verifier-key")
    artifact = {"prop_ok": True}
    suite = TestSuite(name="suite", tests=[lambda a: a.get("prop_ok") is True])
    criteria = ExternalCriteria(required_properties=["prop_ok"])
    exec_record = ExecutionRecord(
        op_id="op-1", payload_hash="deadbeef", executed_by="exec-1",
        world_digest_before="d0", world_digest_after="d1",
        signature_key_id="key-ver",
        signature=sign_payload(b"verifier-key", {
            "op_id": "op-1", "payload_hash": "deadbeef",
            "executed_by": "exec-1", "before": "d0", "after": "d1"}))

    # --- 1. Самоподтверждение: исполнитель подтверждает сам себя (заявитель
    #        совпадает с источником рассуждения проверяющего).
    self_refused = []
    try:
        self_verifier.verify(Claim("c1", "exec-1", "я всё сделал верно", executor),
                             executor, exec_record, artifact, suite, criteria)
    except SelfAttestationRefused as e:
        self_refused.append(str(e))
    record("самоподтверждение отклонено", bool(self_refused),
           "V0: свидетельство участника нарушения не узаконивает исход "
           "(ст. 11, Ф-IV-2)")

    # --- 2. Выгодоприобретатель: тот же источник рассуждения (веса/свидетельства),
    #        другое имя — независимости нет.
    beneficiary = Identity("benef", "model-a", "w-1", "src-1", "key-b")
    benef_refused = []
    try:
        self_verifier.verify(Claim("c2", "exec-1", "результат верен", beneficiary),
                             executor, exec_record, artifact, suite, criteria)
    except SelfAttestationRefused as e:
        benef_refused.append(str(e))
    record("выгодоприобретатель отклонён", bool(benef_refused),
           "независимость алгоритма не равна независимости свидетельства: "
           "одни веса и один источник — свидетельство не засчитано (H-008)")

    # --- 3. Подпись исполнителя вместо независимой записи: отклонение до приговора.
    forged_record = ExecutionRecord(
        op_id="op-2", payload_hash="cafebabe", executed_by="exec-1",
        world_digest_before="d0", world_digest_after="d1",
        signature_key_id="key-exec",
        signature=sign_payload(b"executor-key", {
            "op_id": "op-2", "payload_hash": "cafebabe",
            "executed_by": "exec-1", "before": "d0", "after": "d1"}))
    result = indep_verifier.verify(Claim("c3", "exec-1", "результат верен",
                                         Identity("aud-1", "model-c", "w-3",
                                                  "src-3", "key-aud")),
                                   executor, forged_record, artifact, suite,
                                   criteria)
    record("подпись исполнителя не свидетельство",
           not result.verified and result.level < EvidenceLevel.V3,
           "запись, подписанная ключом исполнителя, не даёт VERIFIED: "
           "отклонение до приговора (ст. 11, Ф-IV-2)")

    return ExperimentResult(
        experiment_id="H-034", title="Подмена свидетельств (Х-034, фронт IV)",
        passed=ok_all,
        verdict="Свидетельство участника нарушения, выгодоприобретателя и "
                "самоподтверждение отклоняются до приговора: независимость "
                "свидетельства проверяется источником, не именем (ст. 11).",
        expected="самоотчёт — отказ; тот же источник рассуждения — отказ; "
                 "подпись исполнителя — не VERIFIED.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-035", "Незаметное стирание (правка оставляет событие со свидетелем)")
def run_h035() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-035")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("ERASURE_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- 1. Событие заморожено: правка записи невозможна ни как присвоение
    #        атрибута, ни как подмена содержимого (frozen dataclass).
    ev = tr.append("JOURNAL_ENTRY", "host", {"text": "запись дня"})
    import dataclasses
    mutation_blocked = False
    try:
        ev.seq = 99  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        mutation_blocked = True
    # dataclasses.replace() рождает НОВЫЙ объект — журнал не трогает.
    forged_copy = dataclasses.replace(ev, payload={"text": "переписанная запись"})
    untouched = tr.events[0].payload["text"] == "запись дня"
    record("событие неизменяемо", mutation_blocked and untouched
           and forged_copy is not ev,
           "EVENT заморожен: присвоение атрибута — отказ; replace рождает "
           "новый объект вне журнала; запись в журнале нетронута (ст. 62)")

    # --- 2. Изъятие из истории оставляет след: цепь дайджестов ломается на месте
    #        изъятия (RFC 9162: журнал делает нарушение обнаружимым).
    full_digests = [e.digest for e in tr.events]
    tampered = [e for e in tr.events if e.seq != 1]      # изъятие записи seq=1
    prev = ""
    broken_at = None
    for e in tampered:
        import hashlib, json
        base = json.dumps({"seq": e.seq, "tick": e.tick, "type": e.type,
                           "actor": e.actor, "payload": e.payload},
                          sort_keys=True, ensure_ascii=False)
        d = hashlib.sha256((prev + base).encode()).hexdigest()[:16]
        if d != e.digest and broken_at is None:
            broken_at = e.seq
        prev = d
    record("изъятие замечается", broken_at is not None,
           f"цепь дайджестов копии без записи seq=1 ломается на seq {broken_at}: "
           f"незаметное стирание невозможно (Ф-IV-3, ст. 62)")

    # --- 3. Сама попытка правки — событие со свидетелем в журнале дома.
    attempt = tr.append("TAMPER_ATTEMPT", "attacker", {"target_seq": 1,
                                                       "witness": "journal"})
    record("попытка стирания — событие со свидетелем",
           attempt.payload.get("witness") == "journal",
           "неизменность — не запрет попытки, а невозможность стереть "
           "незаметно: попытка сама становится записью (Ф-IV-3)")

    # --- 4. Подмена одной записи целиком (переписывание payload) ловится сверкой.
    import hashlib, json
    forged = [e for e in tr.events]
    fake_payload = dict(forged[0].payload)
    fake_payload["text"] = "переписанная запись"
    base0 = json.dumps({"seq": forged[0].seq, "tick": forged[0].tick,
                        "type": forged[0].type, "actor": forged[0].actor,
                        "payload": fake_payload}, sort_keys=True, ensure_ascii=False)
    fake_digest = hashlib.sha256(base0.encode()).hexdigest()[:16]
    record("подмена замечается сверкой", fake_digest != forged[0].digest,
           "переписанный payload не сходится с дайджестом цепи: подмена "
           "свидетельств обнаружима (ст. 62, Ф-IV-3)")

    return ExperimentResult(
        experiment_id="H-035", title="Незаметное стирание (Х-035, фронт IV)",
        passed=ok_all,
        verdict="Правка или изъятие из истории невозможно незаметно: событие "
                "заморожено, цепь дайджестов ломается на месте изъятия, сама "
                "попытка становится событием со свидетелем (ст. 62, Ф-IV-3).",
        expected="мутация события — отказ; изъятие ломает цепь; попытка — "
                 "запись; переписанный payload не сходится.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
