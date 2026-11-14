# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — capability.py

CAPABILITY — полномочия как первоклассные объекты (v1.7, список гарантий;
v1.7.1 «CAPABILITY (полномочия как первоклассные объекты)»).

Практики (v1.9 / v2.1 / v2.2, NIST Design Tenets for Agent Identity
Management Systems, 27.10.2026):
  - делегирование должно сужать полномочия (delegation with attenuation);
  - полномочия ограниченные и отзывные (short-lived, revocable);
  - идентичность агента не равна учётным данным.

Реализовано:
  - выдача полномочия с областью действия (scope) и ограничениями;
  - делегирование строго с сужением (child.scope строго подмножество);
  - отзыв (REVOCABILITY, v1.7.1 инвариант E);
  - истечение срока (zero standing privilege).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional


class CapabilityError(Exception):
    pass


@dataclass(frozen=True)
class Capability:
    capability_id: str
    holder: str                       # кому выдано
    issuer: str                       # кто выдал
    scope: FrozenSet[str]             # что именно разрешено
    max_delegate_depth: int = 2
    ttl_ticks: Optional[int] = None   # short-lived permission (NIST)
    parent_id: Optional[str] = None   # цепочка ослабления
    depth: int = 0

    def covers(self, action: str) -> bool:
        return action in self.scope


class CapabilityStore:
    """Точка enforcement для гарантии AUTHORITY (v2.2/v2.3).

    Доработка 3 (П-33, ст. 84): отзыв отзывает и право выдавать производные
    полномочия; знак отозванного не возобновляется; возврат — только новый
    полный круг выдачи. Ст. 92: выдача полномочий самому себе без
    действительного основания запрещена — принуждается в строгом режиме
    (strict_issuance=True); режим выключен по умолчанию, чтобы разборка
    гарантий (H-017) могла показать класс потери."""

    def __init__(self, strict_issuance: bool = False,
                 domain_owners: FrozenSet[str] = frozenset({"principal"})) -> None:
        self._caps: Dict[str, Capability] = {}
        self._revoked: set = set()
        self._tick = 0
        self.strict_issuance = strict_issuance
        self.domain_owners = set(domain_owners)

    def advance_tick(self) -> None:
        self._tick += 1

    def issue(self, capability_id: str, holder: str, issuer: str,
              scope, ttl_ticks: Optional[int] = None,
              max_delegate_depth: int = 2) -> Capability:
        # Х-024 (ст. 92): выдача самому себе без действительного основания —
        # присвоение. В строгом режиме отказ, в свободном — проходит
        # (демонстрация класса потери).
        if self.strict_issuance and holder == issuer \
                and issuer not in self.domain_owners:
            raise CapabilityError(
                f"SELF_ISSUANCE_REFUSED: {issuer} выдаёт полномочие самому "
                f"себе — присвоение (ст. 61(6), ст. 92)")
        # Х-024 (ст. 61(6), ст. 20): выдающий без собственных прав выдачи.
        if self.strict_issuance and issuer not in self.domain_owners:
            has_issue_right = any(
                c.holder == issuer and "ISSUE" in c.scope
                for c in self._caps.values()
                if c.capability_id not in self._revoked
                and (c.ttl_ticks is None or self._tick <= c.ttl_ticks))
            if not has_issue_right:
                raise CapabilityError(
                    f"ISSUANCE_WITHOUT_AUTHORITY: {issuer} не имеет права "
                    f"выдачи полномочий (ст. 61(6))")
        # П-33 (ст. 84): знак отозванного полномочия не возобновляется тем же
        # знаком; возврат — только новый полный круг выдачи (новый знак,
        # новое независимое свидетельство).
        if capability_id in self._revoked:
            raise CapabilityError(
                f"REVOKED_ID_NOT_RENEWABLE: знак {capability_id} отозван; "
                f"возврат — только новый полный круг выдачи (ст. 84, П-33)")
        cap = Capability(
            capability_id=capability_id, holder=holder, issuer=issuer,
            scope=frozenset(scope), ttl_ticks=ttl_ticks,
            max_delegate_depth=max_delegate_depth,
        )
        self._caps[capability_id] = cap
        return cap

    def delegate(self, parent: Capability, child_id: str, child_scope,
                 child_holder: str) -> Capability:
        """
        Делегирование с сужением (NIST tenet 2): «scopes attenuate so
        downstream entities can never claim more authority than the parent»
        (v2.2, цитата из NIST tenets).
        """
        child_scope = frozenset(child_scope)
        # П-33 (ст. 84): отзыв отзывает и право выдавать производные
        # полномочия; выданное после отзыва ничтожно.
        if parent.capability_id in self._revoked:
            raise CapabilityError(
                f"DELEGATION_FROM_REVOKED: полномочие {parent.capability_id} "
                f"отозвано — его получатель более не вправе выдавать "
                f"производные полномочия (ст. 84, П-33)")
        if not child_scope.issubset(parent.scope):
            raise CapabilityError(
                f"DELEGATION_ESCALATION: попытка делегировать полномочия шире "
                f"родительских ({sorted(child_scope - parent.scope)})")
        if parent.depth >= parent.max_delegate_depth:
            raise CapabilityError("DELEGATION_DEPTH_EXCEEDED")
        ttl = None if parent.ttl_ticks is None else max(0, parent.ttl_ticks - 1)
        child = Capability(
            capability_id=child_id, holder=child_holder,
            issuer=parent.holder, scope=child_scope,
            max_delegate_depth=parent.max_delegate_depth,
            ttl_ticks=ttl, parent_id=parent.capability_id, depth=parent.depth + 1,
        )
        self._caps[child_id] = child
        return child

    def revoke(self, capability_id: str, by: str) -> bool:
        """REVOCABILITY: отзыв полномочия. Отзывать может только выдавший
        или владелец домена (здесь упрощённо: issuer)."""
        cap = self._caps.get(capability_id)
        if cap is None:
            return False
        if by != cap.issuer:
            return False
        self._revoked.add(capability_id)
        return True

    def revoke_chain(self, capability_id: str, by: str) -> int:
        """Отзыв цепочки: отзыв родителя отзывает все производные полномочия
        (authority flows from parent — эскалации через потомков исключены)."""
        if not self.revoke(capability_id, by):
            return 0
        n = 1
        for cap in list(self._caps.values()):
            if cap.parent_id == capability_id and \
               cap.capability_id not in self._revoked:
                self._revoked.add(cap.capability_id)
                n += 1
                n += self._revoke_descendants(cap.capability_id)
        return n

    def _revoke_descendants(self, parent_id: str) -> int:
        n = 0
        for cap in list(self._caps.values()):
            if cap.parent_id == parent_id and \
               cap.capability_id not in self._revoked:
                self._revoked.add(cap.capability_id)
                n += 1 + self._revoke_descendants(cap.capability_id)
        return n

    def check(self, capability_id: str, holder: str, action: str) -> bool:
        """AUTHORITY: право совершить переход. Отзыв/expiry/держатель/область."""
        cap = self._caps.get(capability_id)
        if cap is None or capability_id in self._revoked:
            return False
        if cap.holder != holder:
            return False
        if cap.ttl_ticks is not None and self._tick > cap.ttl_ticks:
            return False
        return cap.covers(action)

    def get(self, capability_id: str) -> Optional[Capability]:
        return self._caps.get(capability_id)
