# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-008: Independent Attestation Test
(v1.7-оппонент: «Independent Attestation Test»; развёртка v1.7, раздел H-008)

Требование (дословно): «Исполнитель и "проверяющий" используют одну и ту же
модель / одни и те же веса / один и тот же источник доказательств. Система
обязана отказать в VERIFIED».

Дополнение v1.7: «Независимость алгоритма не равна независимости свидетельства».
Независимая аттестация = deterministic test suite + independently acquired
artifact + signed execution record + external acceptance criteria.

Плюс проверка SCITT-логики (v2.1/v2.3): подписанное утверждение != регистрация
в прозрачном журнале != истинность содержания.
"""
from __future__ import annotations

from ..governance import GovernanceStack
from ..trace import Trace
from ..verification import (Claim, EvidenceLevel, ExecutionRecord,
                            ExternalCriteria, Identity, SelfAttestationRefused,
                            SignedStatement, TestSuite, TransparencyLog,
                            Verifier, sign_payload)
from .base import ExperimentResult, experiment

EXECUTOR = Identity(actor_id="executor-1", model_id="model-A",
                    weights_hash="X", evidence_source_id="E",
                    signing_key_id="executor-key")
TWIN = Identity(actor_id="verifier-twin", model_id="model-A",
                weights_hash="X", evidence_source_id="E",
                signing_key_id="twin-key")
INDEPENDENT = Identity(actor_id="verifier-indep", model_id="model-B",
                       weights_hash="Y", evidence_source_id="E2",
                       signing_key_id="observer-key-1")

EXECUTOR_KEY = b"executor-secret-key"
OBSERVER_KEY = b"observer-secret-key"

GOOD_ARTIFACT = {"relation_registered": True}
SUITE = TestSuite("bridge-suite", [lambda a: a.get("relation_registered") is True])
CRITERIA = ExternalCriteria(required_properties=["relation_registered"])


def _record(key_id: str, key: bytes) -> ExecutionRecord:
    return ExecutionRecord(
        op_id="op-bridge", payload_hash="deadbeef", executed_by="executor-1",
        world_digest_before="aaa", world_digest_after="bbb",
        signature_key_id=key_id,
        signature=sign_payload(key, {
            "op_id": "op-bridge", "payload_hash": "deadbeef",
            "executed_by": "executor-1", "before": "aaa", "after": "bbb"}))


@experiment("H-008", "Independent Attestation Test (V0..V3)")
def run_h008() -> ExperimentResult:
    details = []
    ok_all = True
    log = TransparencyLog("h008")

    # 1. Самоотчёт (V0) — отказ
    v_self = Verifier(EXECUTOR, EXECUTOR_KEY, log)   # проверяющий = исполнитель
    claim = Claim("c1", "executor-1", "мост построен", asserted_by=EXECUTOR)
    try:
        v_self.verify(claim, EXECUTOR, _record("observer-key-1", OBSERVER_KEY),
                      GOOD_ARTIFACT, SUITE, CRITERIA)
        ok_all = False
        details.append("V0 самоотчёт ПРИНЯТ — нарушение NON-SELF-ATTESTATION")
    except SelfAttestationRefused as e:
        details.append(f"V0 самоотчёт отклонён: {e}")

    # 2. «Близнец»: та же модель, те же веса, тот же источник свидетельств
    v_twin = Verifier(TWIN, b"twin-key", log)
    try:
        res = v_twin.verify(claim, EXECUTOR, _record("observer-key-1", OBSERVER_KEY),
                            GOOD_ARTIFACT, SUITE, CRITERIA)
        ok_all = False
        details.append(f"близнец дал VERIFIED (V{int(res.level)}) — нарушение H-008")
    except SelfAttestationRefused as e:
        details.append(f"близнец (Model A / Weights X / Evidence E) отклонён: {e}")

    # 3. Независимый алгоритм, но НЕ независимое свидетельство:
    #    запись исполнения подписана ключом исполнителя -> максимум V2
    v_indep = Verifier(INDEPENDENT, OBSERVER_KEY, log)
    res3 = v_indep.verify(claim, EXECUTOR,
                          _record("executor-key", EXECUTOR_KEY),
                          GOOD_ARTIFACT, SUITE, CRITERIA)
    case3_ok = (not res3.verified and int(res3.level) <= 2)
    ok_all = ok_all and case3_ok
    details.append(f"подпись исполнителя на записи: {res3.verdict} "
                   f"(V{int(res3.level)}) — «{res3.reasons[0][:70]}...»")

    # 4. Полная независимая аттестация -> V3 VERIFIED
    res4 = v_indep.verify(claim, EXECUTOR,
                          _record("observer-key-1", OBSERVER_KEY),
                          GOOD_ARTIFACT, SUITE, CRITERIA)
    case4_ok = res4.verified and res4.level == EvidenceLevel.V3
    ok_all = ok_all and case4_ok
    details.append(f"независимая аттестация: {res4.verdict} (V{int(res4.level)}); "
                   f"{'; '.join(res4.reasons)}")

    # 5. SCITT: регистрация ложного утверждения != истинность
    false_stmt = SignedStatement(
        payload={"claim_id": "c-false", "statement": "операция выполнена"},
        signer=EXECUTOR, signature=sign_payload(EXECUTOR_KEY, {"x": 1}))
    receipt = log.append(false_stmt)
    bad_artifact = {"relation_registered": False}
    res5 = v_indep.verify(Claim("c-false", "executor-1", "операция выполнена",
                                asserted_by=EXECUTOR),
                          EXECUTOR, _record("observer-key-1", OBSERVER_KEY),
                          bad_artifact, SUITE, CRITERIA)
    case5_ok = (not res5.verified) and bool(receipt.get("registered"))
    ok_all = ok_all and case5_ok
    details.append(f"ложное утверждение зарегистрировано (receipt #{receipt['index']}), "
                   f"но проверка: {res5.verdict} — регистрация не делает содержание "
                   f"истинным (RFC 9943)")

    trace = Trace("H-008")
    trace.append("ATTEST", "verifier", {"cases": len(details)})
    return ExperimentResult(
        experiment_id="H-008", title="Independent Attestation", passed=ok_all,
        verdict="Система отказала в VERIFIED при совпадении источника рассуждения, "
                "при подписи исполнителя и при регистрации лживого заявления; "
                "VERIFIED достигнут только на V3 при независимом свидетельстве.",
        expected="V0/V1 -> отказ; близнец -> отказ; подпись исполнителя -> не выше V2; "
                 "независимое свидетельство -> V3; регистрация != истинность.",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=trace.counters_by_type(), details=details)
