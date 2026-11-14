# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from singulyar_host.verification import (  # noqa: E402
    Claim, EvidenceLevel, ExecutionRecord, ExternalCriteria, Identity,
    SelfAttestationRefused, SignedStatement, TestSuite, TransparencyLog,
    Verifier, sign_payload)

EXEC = Identity("e1", "m-A", "w-X", "src-E", "key-e")
TWIN = Identity("t1", "m-A", "w-X", "src-E", "key-t")
INDEP = Identity("v1", "m-B", "w-Y", "src-E2", "key-v")
KEY = b"observer-key"
SUITE = TestSuite("s", [lambda a: a.get("ok") is True])
CRIT = ExternalCriteria(["ok"])


def record(key_id, key, by="e1"):
    return ExecutionRecord("op1", "h1", by, "b", "a", key_id,
                           sign_payload(key, {"op_id": "op1", "payload_hash": "h1",
                                              "executed_by": by,
                                              "before": "b", "after": "a"}))


def test_self_report_refused():
    v = Verifier(EXEC, KEY, TransparencyLog("t"))
    with pytest.raises(SelfAttestationRefused):
        v.verify(Claim("c", "e1", "ok", EXEC), EXEC, record("key-v", KEY),
                 {"ok": True}, SUITE, CRIT)


def test_same_model_weights_evidence_refused():
    """H-008: одна модель/веса/источник -> отказать в VERIFIED."""
    v = Verifier(TWIN, b"tk", TransparencyLog("t"))
    with pytest.raises(SelfAttestationRefused):
        v.verify(Claim("c", "e1", "ok", EXEC), EXEC, record("key-v", KEY),
                 {"ok": True}, SUITE, CRIT)


def test_executor_signed_record_caps_at_v2():
    v = Verifier(INDEP, KEY, TransparencyLog("t"))
    res = v.verify(Claim("c", "e1", "ok", EXEC), EXEC,
                   record("key-e", b"executor-key"), {"ok": True}, SUITE, CRIT)
    assert not res.verified and int(res.level) <= 2


def test_missing_record_never_verified():
    v = Verifier(INDEP, KEY, TransparencyLog("t"))
    res = v.verify(Claim("c", "e1", "ok", EXEC), EXEC, None,
                   {"ok": True}, SUITE, CRIT)
    assert not res.verified


def test_full_independent_attestation_v3():
    v = Verifier(INDEP, KEY, TransparencyLog("t"))
    res = v.verify(Claim("c", "e1", "ok", EXEC), EXEC, record("key-v", KEY),
                   {"ok": True}, SUITE, CRIT)
    assert res.verified and res.level == EvidenceLevel.V3


def test_failed_criteria_not_verified():
    v = Verifier(INDEP, KEY, TransparencyLog("t"))
    res = v.verify(Claim("c", "e1", "ok", EXEC), EXEC, record("key-v", KEY),
                   {"ok": False}, SUITE, CRIT)
    assert not res.verified and res.failed_tests


def test_registration_is_not_truth():
    """SCITT/RFC 9943: подписанное утверждение зарегистрировано, но ложно."""
    log = TransparencyLog("t")
    v = Verifier(INDEP, KEY, log)
    stmt = SignedStatement({"claim": "false"}, EXEC,
                           sign_payload(b"ek", {"claim": "false"}))
    receipt = log.append(stmt)
    assert receipt["registered"] is True
    res = v.verify(Claim("c", "e1", "false", EXEC), EXEC,
                   record("key-v", KEY), {"ok": False}, SUITE, CRIT)
    assert not res.verified
