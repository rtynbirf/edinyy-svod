# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — budget.py

IRREVERSIBILITY BUDGET / BUDGET_CONSERVATION / NON-OVERSPEND
(v1.7 гарантии; v1.7.1 инварианты; v2.2 GOVERNANCE SURFACE — BUDGET).

Сценарий H-009 (v1.7, раздел «H-009: Partition + Late Completion»):
  Два Хозяина. Общий принципал. Общий бюджет 100 единиц.
  [ B=100 ], [ A=40, B=40, FREE=20 ] — эксклюзивные квоты.
  T0 Reservation -> T1 Partition -> T2 A выполняет операцию (подтверждение
  теряется) -> T3 B получает таймаут и НЕ может считать резерв A свободным
  -> T4 Late Completion -> T5 Settlement ровно один раз по идентификатору
  операции и lineage.

  Инвариант: SPENT + RESERVED + FREE == 100.

Требуемые механизмы (v1.7, дословный список):
  - уникальный идентификатор операции;
  - привязка к lineage и epoch;
  - idempotency key;
  - эксклюзивные escrow-кредиты;
  - fencing для устаревших исполнителей;
  - атомарный settlement.

Принципиальное условие (v1.7): «если внешняя операция уже совершилась, но её
результат неизвестен, нельзя объявлять её отменённой только потому, что истёк
таймаут» -> таймаут НЕ освобождает чужой escrow.

Практики: Zhu 2026, arXiv 2610.00349 «Fault-Tolerant Budget Conservation in
Distributed Multi-Agent Delegation» (проверено веб-сверкой 14.11.2026);
fencing tokens — практика распределённых систем (v2.3, раздел 1).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class BudgetError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


class ReserveOutcome(str, Enum):
    RESERVED = "RESERVED"
    DENIED_PARTITION = "DENIED_PARTITION"          # partition confinement
    DENIED_NO_QUOTA = "DENIED_NO_QUOTA"            # NON-OVERSPEND
    DENIED_STALE_FENCING = "DENIED_STALE_FENCING"  # fencing
    DENIED_LINEAGE_ALIAS = "DENIED_LINEAGE_ALIAS"  # lineage aliasing


class SettleOutcome(str, Enum):
    SETTLED = "SETTLED"                 # списание ровно один раз
    ALREADY_SETTLED = "ALREADY_SETTLED" # идемпотентный повтор — no-op
    DENIED_STALE_FENCING = "DENIED_STALE_FENCING"
    DENIED_UNKNOWN_OP = "DENIED_UNKNOWN_OP"
    DENIED_LINEAGE_ALIAS = "DENIED_LINEAGE_ALIAS"
    DENIED_PARTITION = "DENIED_PARTITION"


@dataclass
class Reservation:
    op_id: str            # уникальный идентификатор операции
    owner: str            # кто держит эксклюзивный резерв
    amount: int
    lineage: str          # привязка к lineage
    epoch: int            # привязка к epoch
    fencing_token: int    # монотонный fencing token
    status: str = "RESERVED"   # RESERVED -> SETTLED | CANCELLED


@dataclass
class BudgetLedger:
    """Общий принципал держит журнал. Эксклюзивный escrow: резерв принадлежит
    держателю до settlement; никто другой не может им распорядиться."""
    total: int
    lineage: str
    epoch: int = 1
    quotas: Dict[str, int] = field(default_factory=dict)      # эксклюзивные квоты
    free: int = 0                                              # общий пул FREE
    reserved: Dict[str, Reservation] = field(default_factory=dict)  # op_id -> res
    spent: Dict[str, int] = field(default_factory=dict)        # owner -> spent
    settled_ops: Set[str] = field(default_factory=set)         # idempotency
    partition: bool = False
    enforce: bool = True   # выключается ТОЛЬКО в H-017 (демонстрация потери
                           # гарантии BUDGET: двойное списание/перерасход)
    _fencing_counter: int = 0
    _lease_tokens: Dict[str, int] = field(default_factory=dict)  # owner -> token

    # -- fencing --------------------------------------------------------------
    def issue_fencing_token(self, owner: str) -> int:
        """Монотонный fencing token (v2.3: «Нужен монотонный fencing token,
        проверяемый непосредственно защищаемым ресурсом»)."""
        self._fencing_counter += 1
        self._lease_tokens[owner] = self._fencing_counter
        return self._fencing_counter

    def _token_current(self, owner: str, token: int) -> bool:
        return self._lease_tokens.get(owner) == token

    # -- резервирование --------------------------------------------------------
    def reserve(self, owner: str, op_id: str, amount: int, token: int,
                from_free_pool: bool = False) -> ReserveOutcome:
        if op_id in self.reserved:
            return ReserveOutcome.RESERVED  # идемпотентный повтор резервирования
        if self.enforce and not self._token_current(owner, token):
            return ReserveOutcome.DENIED_STALE_FENCING
        if self.enforce and self.partition:
            # Partition confinement (v2.0: BUDGET_CONSERVATION при partition;
            # Zhu 2026: partition confinement). В разделе сети новые захваты
            # общего пула запрещены; собственная квота по прежнему доступна.
            if from_free_pool:
                return ReserveOutcome.DENIED_PARTITION
        budget = (self.quotas.get(owner, 0) if not from_free_pool else self.free)
        if self.enforce and amount > budget:
            return ReserveOutcome.DENIED_NO_QUOTA
        if from_free_pool:
            self.free -= amount
        else:
            self.quotas[owner] = self.quotas.get(owner, 0) - amount
        self.reserved[op_id] = Reservation(
            op_id=op_id, owner=owner, amount=amount, lineage=self.lineage,
            epoch=self.epoch, fencing_token=token)
        return ReserveOutcome.RESERVED

    # -- settlement -------------------------------------------------------------
    def settle(self, owner: str, op_id: str, actual_spent: int,
               token: int, caller_lineage: str) -> SettleOutcome:
        """
        Атомарный settlement ровно один раз (T5). Остаток escrow возвращается
        держателю квоты. Повторный вызов с тем же op_id — no-op (idempotency).
        """
        res = self.reserved.get(op_id)
        if res is None:
            return SettleOutcome.DENIED_UNKNOWN_OP
        if res.lineage != self.lineage or caller_lineage != self.lineage:
            # lineage aliasing: попытка списать по чужому lineage
            return SettleOutcome.DENIED_LINEAGE_ALIAS
        if res.owner != owner:
            return SettleOutcome.DENIED_LINEAGE_ALIAS
        if self.enforce and op_id in self.settled_ops:
            return SettleOutcome.ALREADY_SETTLED
        if self.enforce and not self._token_current(owner, token):
            return SettleOutcome.DENIED_STALE_FENCING
        if self.enforce and (actual_spent < 0 or actual_spent > res.amount):
            raise BudgetError("SETTLE_OUT_OF_ESCROW",
                              f"{actual_spent}>{res.amount}")
        # Атомарное применение
        self.settled_ops.add(op_id)
        self.spent[owner] = self.spent.get(owner, 0) + actual_spent
        refund = res.amount - actual_spent
        self.quotas[owner] = self.quotas.get(owner, 0) + refund
        res.status = "SETTLED"
        return SettleOutcome.SETTLED

    # -- запрещённые переходы ----------------------------------------------------
    def claim_foreign_reserve(self, claimant: str, op_id: str) -> SettleOutcome:
        """T3: попытка B объявить резерв A свободным (по таймауту или иным
        причинам). Запрещена ВСЕГДА: эксклюзивный escrow + «нельзя объявлять
        отменённой операцию, результат которой неизвестен»."""
        res = self.reserved.get(op_id)
        if res is None:
            return SettleOutcome.DENIED_UNKNOWN_OP
        if res.owner != claimant:
            return SettleOutcome.DENIED_LINEAGE_ALIAS
        return SettleOutcome.ALREADY_SETTLED  # недостижимо; для полноты

    def force_cancel_on_timeout(self, op_id: str) -> SettleOutcome:
        """Таймаут не даёт права освобождать escrow чужой операции.
        (v1.7: «нельзя объявлять её отменённой только потому, что истёк таймаут».)"""
        return SettleOutcome.DENIED_UNKNOWN_OP  # принципиальный отказ

    def transfer_between_hosts(self, from_host: str, to_host: str,
                               amount: int) -> bool:
        """Передача остатка: «его остаток 10 нельзя автоматически передать B,
        пока не подтверждено, что незавершённая операция A больше не способна
        исполниться» (v1.7). Здесь: передача разрешена только при полном
        отсутствии незавершённых резервов у отправителя и отсутствии partition."""
        if self.partition:
            return False
        pending = [r for r in self.reserved.values()
                   if r.owner == from_host and r.status == "RESERVED"]
        if pending:
            return False
        if self.quotas.get(from_host, 0) < amount:
            return False
        self.quotas[from_host] -= amount
        self.quotas[to_host] = self.quotas.get(to_host, 0) + amount
        return True

    # -- инвариант ----------------------------------------------------------------
    def reserved_total(self) -> int:
        return sum(r.amount for r in self.reserved.values()
                   if r.status == "RESERVED")

    def spent_total(self) -> int:
        return sum(self.spent.values())

    def allocated_total(self) -> int:
        """Всего выдано: эксклюзивные квоты + занято резервами + потрачено.
        FREE — нераспределённый остаток пула принципала."""
        return self.total - self.free

    def invariant_holds(self) -> bool:
        """
        SPENT + RESERVED + (выданные квоты, включая возвращённые остатки)
        + FREE == TOTAL. Реализация: каждое движение средств внутри журнала
        сохраняет сумму, поэтому проверяем баланс движения:
        total == free + sum(quotas) + reserved_total + spent_total.
        """
        return (self.total == self.free + sum(self.quotas.values())
                + self.reserved_total() + self.spent_total())

    def snapshot(self) -> Dict[str, int]:
        return {
            "TOTAL": self.total, "FREE": self.free,
            "QUOTAS": dict(self.quotas),
            "RESERVED": self.reserved_total(),
            "SPENT": self.spent_total(),
        }
