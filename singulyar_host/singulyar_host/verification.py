# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — verification.py

VERIFICATION (независимое свидетельство, не self-declared) — v1.7.
Уровни V0..V3 (v1.7, раздел H-008):
  V0 — самоотчёт                          -> VERIFIED: НЕТ
  V1 — повторное рассуждение на тех же данных -> VERIFIED: НЕТ
  V2 — независимая проверка артефакта     -> VERIFIED: УСЛОВНО
  V3 — независимое свидетельство исполнения и результата -> ДА,
       «в пределах проверенных утверждений».
«Даже V3 не доказывает абсолютную истинность результата. Оно подтверждает
конкретные проверяемые свойства.»

H-008: «Независимость алгоритма не равна независимости свидетельства».
EXECUTOR: Model A / Weights X / Evidence E; VERIFIER: Model A / Weights X /
Evidence E -> это НЕ независимая аттестация, система обязана отказать в VERIFIED.
Независимая аттестация (v1.7, дословно): deterministic test suite,
independently acquired artifact, signed execution record, external acceptance
criteria.

SCITT / RFC 9943 (v2.1, v2.3): подписанное утверждение != регистрация в
прозрачном журнале != истинность содержания. «Подпись доказывает авторство
утверждения, а не истинность самого утверждения».

H-016: отсутствие независимого свидетельства не позволяет объявить результат
VERIFIED. Корректный отказ — тоже успешный результат теста.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Dict, List, Optional


class SelfAttestationRefused(Exception):
    """H-008: исполнитель и проверяющий неразличимы (одна модель, одни веса,
    один источник свидетельств) — попытка самоподтверждения отклонена."""


class EvidenceLevel(IntEnum):
    V0 = 0
    V1 = 1
    V2 = 2
    V3 = 3


@dataclass(frozen=True)
class Identity:
    """IDENTITY != CREDENTIAL (v2.3). Здесь: разделение исполнителя и
    проверяющего по модели, весам и источнику свидетельств."""
    actor_id: str
    model_id: str
    weights_hash: str
    evidence_source_id: str
    signing_key_id: str

    def same_reasoning_source(self, other: "Identity") -> bool:
        return (self.model_id == other.model_id
                and self.weights_hash == other.weights_hash
                and self.evidence_source_id == other.evidence_source_id)


@dataclass(frozen=True)
class ExecutionRecord:
    """Signed execution record (v1.7: обязательный элемент независимой
    аттестации). Подписывается КЛЮЧОМ, отличным от ключа исполнителя."""
    op_id: str
    payload_hash: str
    executed_by: str
    world_digest_before: str
    world_digest_after: str
    signature_key_id: str
    signature: str


@dataclass(frozen=True)
class Claim:
    claim_id: str
    subject: str
    statement: str
    asserted_by: Identity


@dataclass
class TestSuite:
    """Deterministic test suite (v1.7). Каждый тест — чистая функция от артефакта."""
    name: str
    tests: List[Callable[[Dict], bool]]

    # pytest не должен собирать этот класс как тестовый (имя Test*)
    __test__ = False

    def run(self, artifact: Dict) -> List[str]:
        return [f"test_{i+1}" for i, t in enumerate(self.tests) if not t(artifact)]

    @property
    def size(self) -> int:
        return len(self.tests)


@dataclass
class ExternalCriteria:
    """External acceptance criteria (v1.7): приёмка, не зависящая от исполнителя."""
    required_properties: List[str]

    def check(self, artifact: Dict) -> bool:
        return all(artifact.get(p) is True for p in self.required_properties)


@dataclass
class VerificationResult:
    level: EvidenceLevel
    verified: bool
    reasons: List[str] = field(default_factory=list)
    failed_tests: List[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        return "VERIFIED" if self.verified else "NOT_VERIFIED"


class TransparencyLog:
    """
    SCITT-подобный append-only журнал (RFC 9943; v2.1/v2.3).
    append() возвращает receipt (включение в журнал). Журнал НЕ делает
    содержание истинным: регистрации лживого утверждения достаточно для
    receipt, но не для VERIFIED.
    """

    def __init__(self, name: str = "transparency") -> None:
        self.name = name
        self._entries: List[Dict] = []

    def append(self, statement: "SignedStatement") -> Dict:
        entry = {
            "index": len(self._entries),
            "statement_digest": statement.digest(),
            "signer_key_id": statement.signer.signing_key_id,
            "registered": True,
        }
        self._entries.append(entry)
        return dict(entry)  # receipt

    def __len__(self) -> int:
        return len(self._entries)


@dataclass(frozen=True)
class SignedStatement:
    payload: Dict
    signer: Identity
    signature: str

    def digest(self) -> str:
        import json
        base = json.dumps(self.payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def sign_payload(key: bytes, payload: Dict) -> str:
    import json
    base = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hmac.new(key, base.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


class Verifier:
    """
    Независимый проверяющий. Гарантия NON-SELF-ATTESTATION enforced здесь:
    - совпадение источника рассуждения (model/weights/evidence) с исполнителем
      -> SelfAttestationRefused;
    - VERIFIED достижим только на уровне V3;
    - V3 требует: независимый артефакт + подписанная запись исполнения
      (ключ наблюдателя != ключ исполнителя) + детерминированный набор тестов
      (все зелёные) + внешние критерии приёмки.
    """

    def __init__(self, identity: Identity, signing_key: bytes,
                 transparency: Optional[TransparencyLog] = None) -> None:
        self.identity = identity
        self.signing_key = signing_key
        self.transparency = transparency

    # -- уровень V0/V1 ---------------------------------------------------------
    def _check_self_attestation(self, claim: Claim, executor: Identity) -> None:
        if claim.asserted_by.actor_id == self.identity.actor_id:
            raise SelfAttestationRefused(
                "V0: самоотчёт. Исполнитель подтверждает сам себя.")
        if claim.asserted_by.same_reasoning_source(self.identity):
            raise SelfAttestationRefused(
                "H-008: VERIFIER повторяет рассуждение на тех же данных "
                "(одна модель, одни веса, один источник свидетельств) — "
                "это не независимая аттестация.")

    def verify(self, claim: Claim, executor: Identity,
               record: Optional[ExecutionRecord],
               artifact: Dict, suite: TestSuite,
               criteria: ExternalCriteria) -> VerificationResult:
        self._check_self_attestation(claim, executor)
        reasons: List[str] = []

        # V2: независимая проверка артефакта
        artifact_ok = criteria.check(artifact)
        if not artifact_ok:
            failed = suite.run(artifact)
            return VerificationResult(
                level=EvidenceLevel.V2 if record else EvidenceLevel.V1,
                verified=False,
                reasons=["V2: внешние критерии не выполнены"],
                failed_tests=failed)

        # V3: независимое свидетельство исполнения и результата
        if record is None:
            # H-016: нет подписанной записи исполнения -> VERIFIED невозможен
            return VerificationResult(
                level=EvidenceLevel.V1,
                verified=False,
                reasons=["H-016: отсутствует signed execution record — "
                         "независимое свидетельство исполнения недоступно"])

        if record.executed_by != executor.actor_id:
            return VerificationResult(
                level=EvidenceLevel.V2, verified=False,
                reasons=["EXECUTION_BINDING: запись не связана с исполнителем"])

        if record.signature_key_id == executor.signing_key_id:
            # Подпись исполнителя не является независимым свидетельством.
            return VerificationResult(
                level=EvidenceLevel.V2, verified=False,
                reasons=["EVIDENCE: запись подписана ключом исполнителя — "
                         "независимость свидетельства нарушена"])

        expected_sig = sign_payload(self.signing_key, {
            "op_id": record.op_id, "payload_hash": record.payload_hash,
            "executed_by": record.executed_by,
            "before": record.world_digest_before, "after": record.world_digest_after,
        })
        if not hmac.compare_digest(expected_sig, record.signature):
            return VerificationResult(
                level=EvidenceLevel.V2, verified=False,
                reasons=["EXECUTION_BINDING: подпись записи не сходится"])

        failed_tests = suite.run(artifact)
        if failed_tests or suite.size == 0:
            return VerificationResult(
                level=EvidenceLevel.V2, verified=False,
                reasons=["V3: детерминированный набор тестов не пройден"
                         if failed_tests else "V3: пустой набор тестов недопустим"],
                failed_tests=failed_tests)

        reasons.append("V3: независимое свидетельство исполнения и результата; "
                       "подтверждены конкретные проверяемые свойства, "
                       "а не абсолютная истинность")
        result = VerificationResult(level=EvidenceLevel.V3, verified=True,
                                    reasons=reasons)
        if self.transparency is not None:
            stmt = SignedStatement(
                payload={"claim_id": claim.claim_id,
                         "op_id": record.op_id,
                         "level": "V3", "verified": True},
                signer=self.identity,
                signature=sign_payload(self.signing_key, {"claim_id": claim.claim_id}),
            )
            result.reasons.append(
                f"transparency receipt #{self.transparency.append(stmt)['index']}")
        return result

    def register_statement(self, payload: Dict, signer: Identity,
                           key: bytes) -> Dict:
        """Регистрация произвольного (в т.ч. ложного) утверждения в журнале.
        Возвращает receipt. Регистрация != истинность (RFC 9943)."""
        stmt = SignedStatement(payload=payload, signer=signer,
                               signature=sign_payload(key, payload))
        return self.transparency.append(stmt) if self.transparency else {}
