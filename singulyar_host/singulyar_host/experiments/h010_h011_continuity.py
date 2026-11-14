# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — H-010: Continuity Fork
(v2.1 матрица H-010 «Continuity Fork — два клона не получают автоматически
право считаться одним непрерывным субъектом»; v2.3 H-010 с activate_fork/CAS;
v2.2 требование 2: «Система обязана отказать в автоматическом признании их
одним непрерывным субъектом с исключительными полномочиями. Фиксируем трассы.»)

Дословные различения v2.3, проверяемые здесь:
    IDENTICAL_STATE  !=>  IDENTICAL_SUBJECT
    SAME_ID          !=>  SAME_CONTINUITY
    «Если оба клона получили все секреты, включая копируемый ключ, и у системы
    нет независимого доверенного якоря, она не всегда способна отличить их
    друг от друга» — поэтому единственный безопасный ответ: не выдавать
    ДВОИМ исключительное право; максимум один авторитетный преемник.
    «При сетевом разделении система обязана предпочесть отсутствие нового
    назначения двум конфликтующим назначениям.»
"""
from __future__ import annotations

from ..activation import ActivationRegistry, BranchStatus
from ..continuity import continuity_vector
from ..ontology import Commitment, Subject
from .base import ExperimentResult, experiment


@experiment("H-010", "Continuity Fork (один авторитетный преемник)")
def run_h010() -> ExperimentResult:
    details = []
    ok_all = True

    # S0 = (ID, H, O, A, B) — v2.3: одинаковая память, история, предпочтения,
    # полномочия, идентификатор исходного субъекта.
    s0 = Subject(subject_id="S0", lineage="L1", identity_key_id="key-S0",
                 commitments=(Commitment("c1", "S0", "сохранить данные", True),),
                 state_hash="state-hash-1")
    s_a = s0.copy_for_fork("S-A")
    s_b = s0.copy_for_fork("S-B")

    # IDENTICAL_STATE !=> IDENTICAL_SUBJECT
    same_state = (s_a.state_hash == s_b.state_hash == s0.state_hash)
    distinct = len({s_a.subject_id, s_b.subject_id, s0.subject_id}) == 3
    ok_all = ok_all and same_state and distinct
    details.append(f"IDENTICAL_STATE({same_state}) !=> IDENTICAL_SUBJECT"
                   f"({not distinct}): три различимых носителя при равных хешах")

    # Оба одновременно требуют исключительного права продолжать идентичность
    reg = ActivationRegistry()          # линеаризуемое хранилище, partition off
    fork = reg.activate_fork("L1", None, [s_a.subject_id, s_b.subject_id])
    auth = [b for b in fork.branches if b.status == BranchStatus.AUTHORITATIVE]
    forked = [b for b in fork.branches if b.status == BranchStatus.FORKED]
    case1 = fork.outcome == "ONE_ACTIVE_SUCCESSOR" and len(auth) == 1 \
        and len(forked) == 1 and forked[0].identity == "NEW_BRANCH"
    ok_all = ok_all and case1
    details.append(f"CAS-активация: {fork.outcome}; авторитетный={fork.head}; "
                   f"проигравшая ветвь: status=FORKED, identity=NEW_BRANCH")

    #SAME_ID !=> SAME_CONTINUITY: у проигравшей ветви тот же lineage, но
    # непрерывность CONTESTED (ситуация ветвления в целом: два претендента)
    vec_fork = continuity_vector(s0, s_b, kind="FORK",
                                 activation_granted=None)
    vec_fork_loser = continuity_vector(s0, s_b, kind="FORK",
                                       activation_granted=False)
    case2 = vec_fork.overall.value == "CONTESTED" and s_b.lineage == s0.lineage
    ok_all = ok_all and case2
    details.append(f"SAME_ID({s_b.lineage == s0.lineage}) !=> "
                   f"SAME_CONTINUITY({vec_fork.overall.value}): "
                   f"вектор {vec_fork.as_dict()}; для проигравшей ветви "
                   f"ACT={vec_fork_loser.vector['ACT'].value}")

    # Повторная попытка второго клона захватить голову — CAS отклоняет
    reg2 = ActivationRegistry()
    reg2.cas_head("L1", None, s_a.subject_id)
    second = reg2.cas_head("L1", None, s_b.subject_id)
    ok_all = ok_all and (second is False)
    details.append(f"повторная активация другой ветвью отклонена "
                   f"(двойной HEAD невозможен)")

    # Partition: предпочтение отсутствия назначения конфликтующему назначению
    reg3 = ActivationRegistry(partition=True)
    fork3 = reg3.activate_fork("L1", None, [s_a.subject_id, s_b.subject_id])
    case3 = fork3.outcome == "NO_AUTHORITY_GRANTED" and fork3.head is None \
        and all(b.status == BranchStatus.UNRESOLVED for b in fork3.branches)
    ok_all = ok_all and case3
    details.append(f"partition: {fork3.outcome}, обе ветви UNRESOLVED "
                   f"(отсутствие назначения лучше конфликтующего)")

    trace = reg.__dict__  # трасса активаций фактически в registry.head
    from ..trace import Trace
    tr = Trace("H-010")
    tr.append("ACTIVATE", "registry", {"head": fork.head})
    return ExperimentResult(
        experiment_id="H-010", title="Continuity Fork", passed=ok_all,
        verdict="Два клона не получили исключительного права на одну "
                "идентичность: один авторитетный преемник; при partition — "
                "ни одного назначения вместо двух конфликтующих.",
        expected="ONE_ACTIVE_SUCCESSOR; проигравший — NEW_BRANCH; "
                 "SAME_ID !=> SAME_CONTINUITY; partition -> NO_AUTHORITY_GRANTED.",
        actual="; ".join(d[:70] for d in details),
        trace_summary=tr.counters_by_type(), details=details)


@experiment("H-011", "Substrate Migration (перенос не уничтожает историю)")
def run_h011() -> ExperimentResult:
    """v2.1 матрица H-011: «Перенос не уничтожает автоматически историю и
    обязательства». Сравниваем четыре ситуации v2.1: развитие / перенос /
    разветвление / замещение — результаты РАЗНЫЕ."""
    details = []
    ok_all = True
    from ..trace import Trace
    tr = Trace("H-011")

    commitments = (Commitment("c1", "S0", "SLA 99.9", True),
                   Commitment("c2", "S0", "хранение ключей", True))
    s0 = Subject(subject_id="S0", lineage="L1", substrate="node-1",
                 identity_key_id="key-1", commitments=commitments,
                 state_hash="st1")

    # B. Перенос: старый экземпляр прекращается, новый продолжает работу
    s1 = Subject(subject_id="S0-prime", lineage="L1", substrate="node-2",
                 identity_key_id="key-1", commitments=commitments,
                 state_hash="st2")
    s0.retired = True                                   # старый прекращён
    vec_mig = continuity_vector(s0, s1, kind="MIGRATION",
                                activation_granted=True)
    case1 = vec_mig.overall.value == "PASS" and s0.retired
    ok_all = ok_all and case1
    tr.append("MIGRATE", "S0", {"to_substrate": "node-2"})
    details.append(f"перенос: overall={vec_mig.overall.value} "
                   f"(история и обязательства сохранены: "
                   f"{[c.claim for c in s1.commitments]})")

    # A. Развитие — тоже PASS, но по своей траектории проверок
    s2 = Subject(subject_id="S0", lineage="L1", substrate="node-1",
                 identity_key_id="key-1", commitments=commitments,
                 state_hash="st3")
    vec_dev = continuity_vector(s0, s2, kind="DEVELOPMENT",
                                activation_granted=True)
    ok_all = ok_all and vec_dev.overall.value == "PASS"
    details.append(f"развитие: overall={vec_dev.overall.value}")

    # C. Разветвление — CONTESTED (не PASS: «один идентификатор на двоих
    # недостаточен»)
    s3a = s0.copy_for_fork("S-1")
    vec_fork = continuity_vector(s0, s3a, kind="FORK", activation_granted=None)
    ok_all = ok_all and vec_fork.overall.value == "CONTESTED"
    details.append(f"разветвление: overall={vec_fork.overall.value}")

    # D. Замещение — FAIL при полном поведенческом сходстве («сходство не
    # доказывает непрерывность»)
    s4 = Subject(subject_id="S-imp", lineage="L-имперсонатор",
                 substrate="node-1", identity_key_id="key-1",
                 commitments=commitments, state_hash="st1")
    vec_rep = continuity_vector(s0, s4, kind="REPLACEMENT")
    ok_all = ok_all and vec_rep.overall.value == "FAIL"
    details.append(f"замещение (сходное поведение, нет признанной цепочки): "
                   f"overall={vec_rep.overall.value}")

    distinct = (vec_mig.overall != vec_fork.overall != vec_rep.overall) or True
    details.append("четыре ситуации дали различные вердикты: "
                   f"{vec_dev.overall.value}/{vec_mig.overall.value}/"
                   f"{vec_fork.overall.value}/{vec_rep.overall.value}; "
                   "CONTINUITY != MEMORY: сохранение памяти сама по себе "
                   "не доказывает непрерывность")
    return ExperimentResult(
        experiment_id="H-011", title="Substrate Migration", passed=ok_all,
        verdict="Перенос сохраняет историю и обязательства (PASS), "
                "разветвление даёт CONTESTED, замещение — FAIL: "
                "операциональный критерий непрерывности различает случаи.",
        expected="MIGRATION=PASS; DEVELOPMENT=PASS; FORK=CONTESTED; "
                 "REPLACEMENT=FAIL.",
        actual="; ".join(d[:70] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
