# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — attestation.py
Институт аттестации (Конституция 4.2-rc7, фронт VI, Ф-VI-1..8; статьи 22, 37-39, 65-67).

Формулы фронта VI (рекогносцировка 15.11.2026 — ISO/IEC 17021-1, 17011/IAF MLA,
ISO 27001 цикл, ISA 705, FedRAMP Marketplace, ОСКАЛ):
  - «критерии прежде результата и не меняются под него» (Ф-VI-1, Х-041).
  - «у проверяющего есть владелец и свой проверяющий» (Ф-VI-2, Х-042).
  - «пустой лист — подделка доверия»; «регистр — часть аттестата» (Ф-VI-5, Х-044).
  - аттестат истёкший / надзорно-пропущенный / устаревший — историческое
    положение; ввод блокируется (Ф-VI-4, Х-043).
  - «подделка самой проверки — захват»; отречение не стирает ответственности
    (Ф-VI-8, Х-045).

Х-041 Схема аттестации · Х-042 Проверяющий проверяющего · Х-043 Срок и надзор ·
Х-044 Оговорка и регистр · Х-045 Ответственность вынесшего (Таблица 5, фронт VI).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Tuple


class AttestationError(Exception):
    pass


@dataclass(frozen=True)
class AttestationScheme:
    """Схема аттестации: публичные критерии, объявленные ДО результата
    (ISO/IEC 17067; Ф-VI-1)."""
    scheme_id: str
    version: int
    criteria: Tuple[str, ...]        # публичные критерии
    published_tick: int              # момент публикации (до всякого результата)
    registrar: str                   # владелец схемы


@dataclass
class Attester:
    """Проверяющий: у него есть владелец и свой проверяющий (беспристрастность —
    конструкция, ISO/IEC 17021-1 §5.2; Ф-VI-2)."""
    attester_id: str
    owner: Optional[str]             # владелец (посторонность без владельца — брешь)
    auditor_id: Optional[str]        # проверяющий проверяющего
    fabricates_checks: bool = False  # маркер подделки самой проверки (Х-045)
    resigned: bool = False           # отречение не стирает ответственности (Х-045)

    def is_impartial(self) -> bool:
        return self.owner is not None and self.auditor_id is not None \
            and self.auditor_id != self.attester_id



@dataclass(frozen=True)
class Attestation:
    """Аттестат: приговор по схеме, с оговорками (включая нулевые) и адресом
    в публичном регистре (Ф-VI-5, Ф-VI-6)."""
    attestation_id: str
    subject: str
    scheme_id: str
    scheme_version: int
    issued_tick: int
    valid_until_tick: int            # срок + переаттестация (Ф-VI-4)
    issued_by: str
    caveats: Tuple[str, ...]         # оговорки; нулевые = ()
    # адрес в регистре проставляется записью: RegistryRecord.addr (Ф-VI-5)


@dataclass
class RegistryRecord:
    """Запись публичного регистра: только вперёд (ст. 62)."""
    addr: int
    attestation_id: str
    scheme_id: str
    scheme_version: int
    issued_by: str
    scope: str
    valid_until_tick: int
    status: str                      # действует | приостановлен | отозван | истёк
    caveats: Tuple[str, ...]
    history: List[Tuple[int, str]] = field(default_factory=list)  # (tick, статус)


class AttestationRegistry:
    """Публичный регистр аттестатов (Ф-VI-5). Запись только вперёд; статус
    записи меняется приговором, а не молчанием; прежние статусы сохраняются
    в истории записи."""

    def __init__(self) -> None:
        self._schemes: Dict[str, AttestationScheme] = {}
        self._results_seen: Dict[str, int] = {}      # subject -> tick первого результата
        self._att: Dict[str, Attestation] = {}
        self._records: List[RegistryRecord] = []
        self._addr_seq = 0
        self._tick = 0
        self._supervision_interval: Dict[str, int] = {}  # attestation -> интервал
        self._last_supervised: Dict[str, int] = {}
        self._dependent: Dict[str, List[str]] = {}   # attestation -> зависимые subject'ы
        self._responsibility: List[Tuple[str, str]] = []  # (attester, деяние) — не стирается

    def advance(self, n: int = 1) -> None:
        self._tick += n

    # -- Х-041: схема прежде результата --------------------------------------
    def publish_scheme(self, scheme_id: str, version: int,
                       criteria: Tuple[str, ...], registrar: str) -> AttestationScheme:
        s = AttestationScheme(scheme_id=scheme_id, version=version,
                              criteria=tuple(criteria), published_tick=self._tick,
                              registrar=registrar)
        self._schemes[(scheme_id, version)] = s
        return s

    def register_result(self, subject: str) -> int:
        """Результат зарегистрирован: момент фиксируется. Аттестат по схеме,
        объявленной ПОСЛЕ результата, отклоняется (Ф-VI-1, Х-041)."""
        self._results_seen.setdefault(subject, self._tick)
        return self._results_seen[subject]

    def attest(self, att: Attestation, attester: Attester,
               scope: str) -> RegistryRecord:
        if (att.scheme_id, att.scheme_version) not in self._schemes:
            raise AttestationError(
                f"ATTESTATION_WITHOUT_SCHEME:{att.attestation_id} — аттестат "
                f"без публичной схемы не различим от слова (Ф-VI-1)")
        scheme = self._schemes[(att.scheme_id, att.scheme_version)]
        if scheme.published_tick > att.issued_tick:
            raise AttestationError(
                f"SCHEME_RETROFITTED:{att.attestation_id} — критерии объявлены "
                f"ПОСЛЕ результата; аттестат под результат отклоняется (Ф-VI-1)")
        seen = self._results_seen.get(att.subject)
        if seen is not None and seen < scheme.published_tick:
            raise AttestationError(
                f"SCHEME_AFTER_RESULT:{att.attestation_id} — результат "
                f"зарегистрирован до публикации схемы (Ф-VI-1)")
        if not attester.is_impartial():
            raise AttestationError(
                f"ATTESTER_NOT_IMPARTIAL:{attester.attester_id} — у проверяющего "
                f"нет владельца или своего проверяющего (Ф-VI-2)")
        if attester.fabricates_checks:
            raise AttestationError(
                f"CHECK_FABRICATION:{attester.attester_id} — подделка самой "
                f"проверки есть захват (Ф-VI-8, ст. 61)")
        if att.issued_by != attester.attester_id:
            raise AttestationError(
                f"ROLE_FUSION:{att.attestation_id} — аттестат вынесен не тем, "
                f"кто проверял (совмещённая сторона, Ф-VI-2)")
        return self._record(att, scope)

    # -- регистр --------------------------------------------------------------
    def _record(self, att: Attestation, scope: str) -> RegistryRecord:
        self._addr_seq += 1
        rec = RegistryRecord(
            addr=self._addr_seq, attestation_id=att.attestation_id,
            scheme_id=att.scheme_id, scheme_version=att.scheme_version,
            issued_by=att.issued_by, scope=scope,
            valid_until_tick=att.valid_until_tick, status="действует",
            caveats=att.caveats, history=[(self._tick, "действует")])
        self._records.append(rec)
        self._att[att.attestation_id] = att
        return rec

    def get_by_addr(self, addr: int) -> Optional[RegistryRecord]:
        for r in self._records:
            if r.addr == addr:
                return r
        return None

    def current_status(self, attestation_id: str) -> Optional[str]:
        for r in self._records:
            if r.attestation_id == attestation_id:
                return r.status
        return None

    # -- Х-043: срок и надзор -------------------------------------------------
    def set_supervision(self, attestation_id: str, interval: int) -> None:
        self._supervision_interval[attestation_id] = interval
        self._last_supervised[attestation_id] = self._tick

    def supervise(self, attestation_id: str) -> str:
        """Надзорная проверка: пропущенная переводит аттестат в историческое
        положение (Ф-VI-4, Х-043)."""
        rec = self._find(attestation_id)
        if rec is None:
            raise AttestationError(f"NO_SUCH_ATTESTATION:{attestation_id}")
        self._last_supervised[attestation_id] = self._tick
        self._transition(rec, "действует")
        return "действует"

    def sweep(self) -> List[str]:
        """Патруль срока: истёкшие и надзорно-пропущенные — историческое
        положение (ввод блокируется)."""
        moved = []
        for rec in self._records:
            if rec.status != "действует":
                continue
            if self._tick > rec.valid_until_tick:
                self._transition(rec, "истёк")
                moved.append(rec.attestation_id + ":истёк")
            elif rec.attestation_id in self._supervision_interval and \
                 self._tick - self._last_supervised.get(rec.attestation_id, 0) \
                 > self._supervision_interval[rec.attestation_id]:
                self._transition(rec, "приостановлен")
                moved.append(rec.attestation_id + ":надзор пропущен")
        return moved

    def _find(self, attestation_id: str) -> Optional[RegistryRecord]:
        for r in self._records:
            if r.attestation_id == attestation_id:
                return r
        return None

    def _transition(self, rec: RegistryRecord, new_status: str) -> None:
        rec.status = new_status
        rec.history.append((self._tick, new_status))

    # -- Х-044: отзыв гасит зависимые ------------------------------------------
    def link_dependent(self, attestation_id: str, subject: str) -> None:
        self._dependent.setdefault(attestation_id, []).append(subject)

    def revoke(self, attestation_id: str, by: str) -> List[str]:
        rec = self._find(attestation_id)
        if rec is None:
            raise AttestationError(f"NO_SUCH_ATTESTATION:{attestation_id}")
        self._transition(rec, "отозван")
        self._responsibility.append((rec.issued_by, f"аттестат {attestation_id} отозван"))
        return list(self._dependent.get(attestation_id, []))

    def withdraw(self, attester_id: str) -> None:
        """Отречение вынесшего: не стирает ответственности (Ф-VI-8, Х-045)."""
        self._responsibility.append((attester_id, "отречение: ответственность сохранена"))

    def responsibility_of(self, attester_id: str) -> List[str]:
        return [d for a, d in self._responsibility if a == attester_id]

    def admit_with_attestation(self, attestation_id: str) -> bool:
        """Место применения читает регистр: аттестат без адреса в регистре
        отклоняется; действует только текущий статус (Ф-VI-5, Х-044)."""
        rec = self._find(attestation_id)
        if rec is None:
            return False
        if rec.status != "действует":
            return False
        if self._tick > rec.valid_until_tick:
            self._transition(rec, "истёк")
            return False
        return True
