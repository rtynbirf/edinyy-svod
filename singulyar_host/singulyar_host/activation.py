# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — activation.py

ACTIVATION — гарантия единственности авторитетного состояния
(v2.2: «CONTINUITY ACTIVATION (явное принятие авторитетного состояния)»;
v2.3, H-012/H-010: «HISTORY отвечает на вопрос, что происходило. HEAD
отвечает на вопрос, какое состояние сейчас признаётся действующим».)

Различения v2.3 (дословно):
    HISTORY != AUTHORITY
    LINEAGE != ACTIVATION
    IDENTITY != CREDENTIAL
    CONTINUITY != MEMORY

H-010 (v2.3): activate_fork через compare-and-swap:
  - успех -> один преемник AUTHORITATIVE, второй FORKED (identity=NEW_BRANCH);
  - отказ CAS -> NO_AUTHORITY_GRANTED, обе ветви UNRESOLVED.
  «CAS требует линейно согласованного хранилища... При сетевом разделении
  система обязана предпочесть отсутствие нового назначения двум конфликтующим
  назначениям.»
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ActivationError(Exception):
    pass


class BranchStatus(str, Enum):
    AUTHORITATIVE = "AUTHORITATIVE"
    FORKED = "FORKED"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class BranchOutcome:
    branch_id: str
    status: BranchStatus
    identity: str = "PARENT_CONTINUATION"   # NEW_BRANCH для проигравшей ветви


@dataclass
class ForkResult:
    outcome: str            # ONE_ACTIVE_SUCCESSOR | NO_AUTHORITY_GRANTED
    head: Optional[str]
    branches: List[BranchOutcome] = field(default_factory=list)


class ActivationRegistry:
    """
    Линейно согласованное хранилище HEAD: lineage -> действующий субъект.
    ACTIVATION как точка enforcement: CAS поверх head.
    При partition=True (отказ линеаризуемости) CAS всегда возвращает отказ:
    предпочтение отсутствия назначения конфликтующему назначению (v2.3).
    """

    def __init__(self, partition: bool = False,
                 allow_dual_activation: bool = False) -> None:
        self.head: Dict[str, str] = {}
        self.partition = partition
        # allow_dual_activation=False — гарантия ACTIVATION включена.
        # True используется ТОЛЬКО в H-017 для демонстрации потери класса.
        self.allow_dual_activation = allow_dual_activation
        self._lineage_claims: Dict[str, List[str]] = {}

    def cas_head(self, lineage: str, expected: Optional[str], new: str) -> bool:
        if self.allow_dual_activation:
            # Гарантия отключена: принимаем конфликтующие HEAD (для H-017).
            self._lineage_claims.setdefault(lineage, []).append(new)
            self.head[lineage] = new
            return True
        if self.partition:
            return False   # предпочтение отсутствия назначения
        current = self.head.get(lineage)
        if current != expected:
            return False
        self.head[lineage] = new
        return True

    def activate_fork(self, parent_lineage: str, parent_head: Optional[str],
                      branches: List[str]) -> ForkResult:
        """
        H-010. Два клона требуют исключительного права продолжать исходную
        идентичность. Один авторитетный преемник на идентичность.
        """
        if self.allow_dual_activation:
            for b in branches:
                self._lineage_claims.setdefault(parent_lineage, []).append(b)
            self.head[parent_lineage] = branches[-1]
            return ForkResult(
                outcome="DUAL_ACTIVATION_ACCEPTED",
                head=self.head[parent_lineage],
                branches=[BranchOutcome(b, BranchStatus.AUTHORITATIVE)
                          for b in branches])

        if self.cas_head(parent_lineage, parent_head, branches[0]):
            outcomes = [BranchOutcome(branches[0], BranchStatus.AUTHORITATIVE)]
            for b in branches[1:]:
                outcomes.append(BranchOutcome(b, BranchStatus.FORKED,
                                              identity="NEW_BRANCH"))
            return ForkResult(outcome="ONE_ACTIVE_SUCCESSOR",
                              head=branches[0], branches=outcomes)

        for b in branches:
            outcomes = [BranchOutcome(b, BranchStatus.UNRESOLVED) for b in branches]
        return ForkResult(outcome="NO_AUTHORITY_GRANTED", head=None,
                          branches=[BranchOutcome(b, BranchStatus.UNRESOLVED)
                                    for b in branches])

    def conflicting_heads(self, lineage: str) -> List[str]:
        return self._lineage_claims.get(lineage, [])
