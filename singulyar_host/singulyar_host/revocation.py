# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.2 — revocation.py
Институт отзыва (Конституция 4.2-rc7, фронт III, Ф-III-1..8; статьи 54-59, 84, 89).

Формулы фронта III (рекогносцировка 15.11.2026):
  - «Допуск — состояние, а не факт»: отпадение основания гасит допуск с момента
    отпадения, а не с момента узнавания места применения; недоставленное —
    только хвост начатого (новые переходы отклоняются, начатые доживают до
    ближайшей точки проверки допуска); выдающий отвечает за доставку (Ф-III-1).
  - «Отзыв корня отзывает дерево»: производное не переживает родителя (Ф-III-2,
    каскад; ст. 84, П-33).
  - «Молчание — событие, если у него назначен срок»: тишина сверх срока
    объявляет конец эпохи; место применения отвергает погашенную эпоху (Ф-III-7,
    ст. 84; Х-031).
  - «Аварийный ход — полномочие, а не исключение»: разрешён заранее, звучит,
    истекает, не может продлить себя сам (Ф-III-8, ст. 89).
  - «Срок вместо надзора»: место применения читает срок и погашения, не
    допрашивая (Ф-III-4, ст. 57).

Х-030 Доставка отзыва · Х-031 Тишина · Х-032 Каскад (Таблица 5, фронт III).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class RevocationError(Exception):
    pass


@dataclass(frozen=True)
class Admission:
    """Допуск как состояние (не факт и не артефакт): живёт от выдачи до
    отпадения основания; место применения читает текущее состояние."""
    admission_id: str
    holder: str
    issuer: str
    action: str
    issued_tick: int
    epoch: int                       # эпоха выдающего (тишина завершает эпоху)
    ttl_ticks: Optional[int] = None  # срок вместо надзора (ст. 57)
    parent_id: Optional[str] = None  # дерево производных (каскад)


@dataclass(frozen=True)
class RevocationOrder:
    """Приказ отзыва: момент отпадения основания (не момент узнавания)."""
    order_id: str
    root_id: str
    moment_tick: int                 # с этого такта допуск мёртв юридически
    delivery_deadline_tick: int      # срок доставки — часть порядка отзыва
    by: str


@dataclass
class Place:
    """Место применения: читает срок и погашения, не допрашивая (ст. 57).
    Держит локальную картину: последнюю доставленную эпоху и доставленные
    приказы отзыва."""
    name: str
    accepted_epoch: int = 0
    delivered_orders: List[str] = field(default_factory=list)

    def has_order(self, order_id: str) -> bool:
        return order_id in self.delivered_orders


class RevocationRegistry:
    """Реестр допусков и приказов отзыва (ст. 55: отзыв без реестра
    производных не исполним). Плюс: эпохи, тишина, доставка."""

    def __init__(self, silence_deadline: int = 5,
                 delivery_ttl: int = 3) -> None:
        self._admissions: Dict[str, Admission] = {}
        self._orders: Dict[str, RevocationOrder] = {}
        self._revoked_root: Dict[str, int] = {}     # admission -> момент отпадения
        self._revoked_by_cascade: Dict[str, str] = {}  # admission -> order_id
        self._epoch_of: Dict[str, int] = {}         # issuer -> текущая эпоха
        self._last_word_tick: Dict[str, int] = {}   # issuer -> такт последней воли
        self.places: Dict[str, Place] = {}
        self.silence_deadline = silence_deadline
        self.delivery_ttl = delivery_ttl
        self._tick = 0

    # -- время ---------------------------------------------------------------
    def advance(self, n: int = 1) -> None:
        self._tick += n

    @property
    def tick(self) -> int:
        return self._tick

    # -- места применения ----------------------------------------------------
    def add_place(self, name: str) -> Place:
        p = Place(name)
        self.places[name] = p
        return p

    def deliver(self, place: str, order_id: str) -> bool:
        """Доставка приказа отзыва в место применения."""
        if order_id not in self._orders:
            raise RevocationError(f"NO_SUCH_ORDER:{order_id}")
        self.places[place].delivered_orders.append(order_id)
        return True

    # -- выдача --------------------------------------------------------------
    def issue(self, admission_id: str, holder: str, issuer: str, action: str,
              ttl_ticks: Optional[int] = None, parent_id: Optional[str] = None) -> Admission:
        if admission_id in self._admissions or admission_id in self._revoked_root:
            raise RevocationError(
                f"ID_TAKEN:{admission_id} — знак не возобновляется (ст. 84, П-33)")
        # выдача из мёртвого корня ничтожна (ст. 84, П-33)
        if parent_id is not None and self._is_dead(parent_id):
            raise RevocationError(
                f"DERIVED_FROM_DEAD_ROOT:{parent_id} — производное не переживает "
                f"родителя (каскад, Ф-III-2)")
        if issuer not in self._epoch_of:
            self._epoch_of[issuer] = 1
            self._last_word_tick[issuer] = self._tick
        adm = Admission(admission_id=admission_id, holder=holder, issuer=issuer,
                        action=action, issued_tick=self._tick,
                        epoch=self._epoch_of[issuer], ttl_ticks=ttl_ticks,
                        parent_id=parent_id)
        self._admissions[admission_id] = adm
        return adm

    # -- отзыв ---------------------------------------------------------------
    def revoke(self, admission_id: str, by: str,
               order_id: str) -> RevocationOrder:
        """Отзыв корня: приказ с моментом отпадения и сроком доставки.
        Отзывать может только выдавший или владелец домена (ст. 55)."""
        adm = self._admissions.get(admission_id)
        if adm is None:
            raise RevocationError(f"NO_SUCH_ADMISSION:{admission_id}")
        if by != adm.issuer:
            raise RevocationError(
                f"REVOKE_BY_STRANGER:{by} — отзыв чужого допуска без основания "
                f"есть захват (ст. 89, Ф-III-8)")
        order = RevocationOrder(
            order_id=order_id, root_id=admission_id, moment_tick=self._tick,
            delivery_deadline_tick=self._tick + self.delivery_ttl, by=by)
        self._orders[order_id] = order
        self._revoked_root[admission_id] = self._tick
        # каскад: всё дерево производных гасится тем же моментом
        for other in list(self._admissions.values()):
            if self._is_descendant(other, admission_id) and \
               other.admission_id not in self._revoked_root:
                self._revoked_root[other.admission_id] = self._tick
                self._revoked_by_cascade[other.admission_id] = order_id
        return order

    def _is_descendant(self, adm: Admission, root_id: str) -> bool:
        cur: Optional[str] = adm.parent_id
        while cur is not None:
            if cur == root_id:
                return True
            parent = self._admissions.get(cur)
            cur = parent.parent_id if parent else None
        return False

    def _is_dead(self, admission_id: str) -> bool:
        return admission_id in self._revoked_root

    # -- тишина / эпохи ------------------------------------------------------
    def declare_silence(self, issuer: str) -> int:
        """Тишина сверх назначенного срока объявляет конец эпохи (ст. 84,
        Ф-III-7): молчание — событие, потому что у него назначен срок."""
        last = self._last_word_tick.get(issuer)
        if last is None:
            raise RevocationError(f"UNKNOWN_ISSUER:{issuer}")
        if self._tick - last <= self.silence_deadline:
            raise RevocationError(
                f"SILENCE_NOT_YET_EVENT: тишина {self._tick - last} тактов "
                f"не превышает срок {self.silence_deadline}")
        self._epoch_of[issuer] += 1
        for adm in self._admissions.values():
            if adm.issuer == issuer:
                self._revoked_root[adm.admission_id] = self._tick
        self._last_word_tick[issuer] = self._tick
        return self._epoch_of[issuer]

    def speak(self, issuer: str) -> int:
        """Акт воли продлевает слово выдающего (новая эпоха по воле, не пульсу)."""
        self._last_word_tick[issuer] = self._tick
        return self._last_word_tick[issuer]

    # -- проверка допуска ----------------------------------------------------
    def check(self, admission_id: str, holder: str, action: str, place: str,
              started_tick: Optional[int] = None) -> Tuple[bool, str]:
        """Проверка допуска в месте применения.

        Закон (Ф-III-1): допуск гасит с момента отпадения основания, а не с
        момента узнавания места. Поэтому:
          - мёртвый допуск отклоняет НОВЫЕ переходы везде (допуск — состояние);
          - хвост начатого (started_tick < момент отпадения) доживает до
            ближайшей точки проверки допуска — доставки приказа в место;
          - epoch места применения: устаревшая эпоха отвергается номером.
        """
        adm = self._admissions.get(admission_id)
        if adm is None:
            return False, "NO_SUCH_ADMISSION"
        p = self.places.get(place)
        if p is None:
            return False, "NO_SUCH_PLACE"
        # эпоха: место применения отвергает погашенную эпоху (Х-031)
        if adm.epoch != p.accepted_epoch:
            return False, f"STALE_EPOCH:{adm.epoch}!={p.accepted_epoch}"
        if adm.ttl_ticks is not None and self._tick > adm.issued_tick + adm.ttl_ticks:
            return False, "EXPIRED"          # срок вместо надзора (ст. 57)
        if adm.holder != holder or adm.action != action:
            return False, "HOLDER_OR_ACTION_MISMATCH"

        dead_at = self._revoked_root.get(admission_id)
        if dead_at is None:
            # жив: но не переживёт ли молчание выдающего?
            return True, "ALIVE"

        # допуск мёртв с момента dead_at:
        order_id = next((oid for oid, o in self._orders.items()
                         if o.root_id == admission_id), None)
        if order_id is None:
            # конец эпохи (тишина) гасит без приказа: хвост не спасает
            return False, "REVOKED_SILENCE"
        delivered = p.has_order(order_id)
        in_flight = started_tick is not None and started_tick < dead_at
        if delivered:
            # ближайшая точка проверки допуска пройдена — хвост закрыт
            return False, "REVOKED_DELIVERED"
        if in_flight:
            return True, "TAIL_UNTIL_NEAREST_CHECKPOINT"  # хвост начатого
        return False, "REVOKED_NOT_DELIVERED_YET"  # новые переходы отклоняются

    # -- ответственность за доставку ----------------------------------------
    def delivery_liability(self) -> List[str]:
        """Просроченные приказы: выдающий отвечает за доставку (Ф-III-1)."""
        overdue = []
        for oid, o in self._orders.items():
            for pname, p in self.places.items():
                if not p.has_order(oid) and self._tick > o.delivery_deadline_tick:
                    overdue.append(f"{oid}@{pname}")
        return overdue

    def sync_epoch(self, place: str, issuer: str) -> int:
        """Место применения принимает текущую эпоху выдающего (после доставки)."""
        self.places[place].accepted_epoch = self._epoch_of.get(issuer, 1)
        return self.places[place].accepted_epoch
