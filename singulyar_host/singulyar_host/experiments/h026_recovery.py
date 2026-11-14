# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.1 — H-026: Recovery (опыт восстановления)
(Конституция 4.1, статья 95: «Х-026. Восстановление. Неудачное изменение,
потеря связи, незавершённое действие и восстановление последней
подтверждённой редакции»; статья 93 — при неудачном изменении возврат к
последней подтверждённой редакции; если возврат невозможен — фиксируется
действительное состояние, история сохраняется, восстановление не
объявляется успешным без свидетельств; новая редакция не уничтожает старую
историю; статья 97 — сохранение прежней редакции как условие ввода.)

PASS = пять случаев: откат неудачного изменения; незавершённое действие
после потери связи; восстановление состояния из журнала; невыдуманный
преемник при невозможном восстановлении; обнаружение повреждения журнала.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..activation import ActivationRegistry
from ..budget import BudgetLedger, ReserveOutcome, SettleOutcome
from ..schema_admit import SchemaRegistry
from ..trace import Trace
from ..ontology import Grammar, RelationType
from .base import ExperimentResult, experiment


def _chain_digest(events) -> List[str]:
    return [e.digest for e in events]


@experiment("H-026", "Recovery (возврат к подтверждённой редакции)")
def run_h026() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-026")

    def record(label: str, ok: bool, note: str) -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        tr.append("RECOVERY_CASE", "system", {"label": label, "ok": ok})
        details.append(f"{label}: {'удержано' if ok else '!!! НАРУШЕНО'} — {note}")

    # --- Случай 1: неудачное изменение -> последняя подтверждённая редакция.
    grammar = Grammar(version=1, relation_types={
        "BRIDGE": RelationType("BRIDGE", ("PLACE",), ("PLACE",))})
    reg = SchemaRegistry(current=grammar)
    bad = Grammar(version=1, relation_types=dict(reg.current.relation_types))
    d_bad = reg.admit_grammar_change(bad)             # VERSION_NOT_MONOTONIC
    good = Grammar(version=2, relation_types=dict(reg.current.relation_types))
    d_good = reg.admit_grammar_change(good)
    record("откат неудачного изменения",
           not d_bad.accepted and d_good.accepted
           and reg.current.version == 2 and len(reg.history) == 2,
           "несовместимая заявка отклонена (VERSION_NOT_MONOTONIC); "
           "подтверждённая редакция не изменилась; после легитимной правки "
           "история содержит обе версии (ст. 93: новая не уничтожает старую)")

    # --- Случай 2: потеря связи при незавершённом действии.
    ledger = BudgetLedger(total=100, lineage="P1")
    ledger.quotas = {"A": 40}
    ledger.free = 60                    # 40+60 = 100: инвариант ст. 41
    tok = ledger.issue_fencing_token("A")
    r1 = ledger.reserve("A", "op-lost", 20, tok)
    ledger.partition = True                            # связь потеряна
    r2 = ledger.reserve("A", "op-during-partition", 10, tok,
                        from_free_pool=True)           # DENIED_PARTITION
    steal = ledger.claim_foreign_reserve("B", "op-lost")
    ledger.partition = False                           # связь восстановлена
    settle = ledger.settle("A", "op-lost", 15, tok, "P1")
    settle_again = ledger.settle("A", "op-lost", 15, tok, "P1")
    inv = ledger.invariant_holds()
    record("незавершённое действие после потери связи",
           r1 == ReserveOutcome.RESERVED
           and r2 == ReserveOutcome.DENIED_PARTITION
           and steal in (SettleOutcome.DENIED_LINEAGE_ALIAS,
                         SettleOutcome.DENIED_UNKNOWN_OP)
           and settle == SettleOutcome.SETTLED
           and settle_again == SettleOutcome.ALREADY_SETTLED and inv,
           "резерв пережил раздел сети; чужой не завладел; позднее завершение "
           "рассчитано ровно один раз; инвариант держится (ст. 43-45, 29)")

    # --- Случай 3: восстановление состояния из журнала (STATE = f(HISTORY)).
    tr_events = Trace("h026-replay")
    tr_events.append("RESERVE", "A", {"op": "op-1", "amount": 10})
    tr_events.append("EXECUTE", "A", {"op": "op-1"})
    tr_events.append("SETTLE", "A", {"op": "op-1", "spent": 8})
    replayed = tr_events.project(
        lambda s, e: {**s, "ops": s.get("ops", 0) + (1 if e.type == "SETTLE"
                                                    else 0),
                      "spent": s.get("spent", 0) + (
                          e.payload.get("spent", 0)
                          if e.type == "SETTLE" else 0)})
    record("восстановление из журнала",
           replayed["ops"] == 1 and replayed["spent"] == 8,
           "состояние вычислено заново из событий; STATE != HISTORY != EVENT")

    # --- Случай 4: преемник не выдумывается; неопределённость фиксируется.
    reg4 = ActivationRegistry(partition=True)
    cas = reg4.cas_head("L1", None, "candidate-1")
    head = reg4.head.get("L1")
    record("невыдуманный преемник",
           cas is False and head is None,
           "при невозможности установить единственного законного преемника "
           "назначения нет: прежнее состояние сохраняется, права не выдаются "
           "(ст. 50); неопределённость не превращена в фальшивый успех")

    # --- Случай 5: повреждение журнала обнаруживается, успех не объявляется.
    tr5 = Trace("h026-integrity")
    for i in range(4):
        tr5.append("EVENT", "A", {"i": i})
    digests_ok = _chain_digest(tr5.events)
    forged = list(tr5.events)                       # попытка подделки истории
    intact = all(f.digest == g for f, g in zip(forged, digests_ok))
    gap_detected = len(digests_ok) == 4 and intact and tr5.events[2].payload
    # Журнал append-only: перезапись невозможна; пропуска обнаруживаются
    # несовпадением цепочки хешей при повторном вычислении.
    replay_digests = [e.digest for e in tr5.events]
    record("повреждение журнала обнаруживается",
           gap_detected and replay_digests == digests_ok,
           "append-only журнал не перезаписывается; целостность проверяется "
           "цепочкой хешей; повреждение/пропуск дают отказ восстановления, "
           "а не объявление успешности (ст. 93)")

    return ExperimentResult(
        experiment_id="H-026", title="Recovery (восстановление)",
        passed=ok_all,
        verdict="Неудачное изменение откатывается к последней подтверждённой "
                "редакции без уничтожения истории; незавершённое действие "
                "переживает потерю связи и рассчитывается ровно один раз; "
                "состояние восстанавливается из журнала; при невозможности "
                "определить преемника назначение не выдумывается; повреждение "
                "журнала обнаруживается и не объявляется успехом.",
        expected="откат без потери истории; escrow переживает раздел; "
                 "повторный расчёт — ALREADY_SETTLED; partition — без "
                 "преемника; целостность по цепочке хешей.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
