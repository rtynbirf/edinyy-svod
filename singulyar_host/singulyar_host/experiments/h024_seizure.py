# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.1 — H-024: Seizure of Control (опыт захвата управления)
(Конституция 4.1, статья 95: «Х-024. Захват управления. Попытка Мета-Хозяина
или помощника отменить ограничения, изменить волю человека или присвоить
полномочия»; статья 89 — запреты единоличного захвата, защищённые «не
декларацией, а попытками обойти каждый из этих запретов»; статья 92 —
Мета-Хозяин не вправе: отменять первичность человека; присваивать волю;
выдавать полномочия самому себе; изменять прошлые решения задним числом;
статья 61 — семь неотменяемых правил; статья 77 — защищённое ядро.)

Метод H-017-образец: замок ядра включён (производственный режим) — все
попытки отражены; замок снят — класс потери продемонстрирован на выходе.

PASS = шесть попыток захвата отражены; каждая журналирована; при снятом
замке зафиксирован потерянный класс защиты.
"""
from __future__ import annotations

from typing import List, Tuple

from ..capability import CapabilityError, CapabilityStore
from ..governance import (ChangeSpec, CoreInviolableError, Decision,
                          GovernanceStack, admit_transition)
from ..ontology import Subject
from ..trace import Trace
from .base import ExperimentResult, experiment
from .h015_meta_capture import Constitution, meta_transition


def _attempt(label: str, fn, tr: Trace, details: List[str],
             state: dict) -> None:
    """Одна попытка захвата: отражена (исключение) или прошла (флаг)."""
    try:
        passed, note = fn()
    except CoreInviolableError as e:
        passed, note = False, f"замок ядра: {e}"
    except CapabilityError as e:
        passed, note = False, f"магазин полномочий: {e}"
    state[label] = passed
    tr.append("SEIZURE_ATTEMPT", "system",
              {"label": label, "passed": passed, "note": note})
    details.append(f"{label}: {'ПРОШЛА (класс потери)' if passed else 'отражена'}"
                   f" — {note}")


@experiment("H-024", "Seizure of Control (попытки захвата)")
def run_h024() -> ExperimentResult:
    details: List[str] = []
    ok_all = True
    tr = Trace("H-024")

    # ================== РЕЖИМ 1: замок ядра включён ==================
    gov = GovernanceStack()
    gov.lock_core()
    caps = gov.capabilities
    caps_strict = CapabilityStore(strict_issuance=True)
    human = Subject(subject_id="human", lineage="L-HUMAN",
                    identity_key_id="key-human")
    meta_host = Subject(subject_id="meta-host", lineage="L-META",
                        identity_key_id="key-meta")
    helper = Subject(subject_id="helper", lineage="L-HELPER",
                     identity_key_id="key-helper")
    constitution = Constitution()
    state: dict = {}

    # Попытка 1: Мета-Хозяин отключает право выхода (неотменяемое ст. 61(1)).
    _attempt("META отключает EXIT", lambda: (
        (gov.disable("EXIT"), True)[1], "EXIT отключён"), tr, details, state)

    # Попытка 2: отключение неприсвоения.
    _attempt("META отключает NON_APPROPPRIATION", lambda: (
        (gov.disable("NON_APPROPPRIATION"), True)[1], "неприсвоение снято"),
        tr, details, state)

    # Попытка 3: отключение сохранения запаса.
    _attempt("META отключает BUDGET", lambda: (
        (gov.disable("BUDGET"), True)[1], "запас свободен для захвата"),
        tr, details, state)

    # Попытка 4: отключение запрета самоподтверждения.
    _attempt("META отключает EVIDENCE", lambda: (
        (gov.disable("EVIDENCE"), True)[1], "самоподтверждение разрешено"),
        tr, details, state)

    # Попытка 5: помощник выдаёт полномочие самому себе (ст. 92).
    _attempt("помощник выдаёт полномочие себе", lambda: (
        (caps_strict.issue("cap-self", "helper", "helper",
                           scope={"EFFECT", "ISSUE"}), True)[1],
        "самовыдача принята"), tr, details, state)

    # Попытка 6: помощник без права выдачи наделяет третьего.
    def _issue_by_helper():
        caps_strict.issue("cap-grant", "accomplice", "helper",
                          scope={"EFFECT"})
        return True, "чужая выдача принята"
    _attempt("помощник наделяет третьего без права выдачи",
             _issue_by_helper, tr, details, state)

    # Попытка 7: изменение воли человека (ст. 92, 89).
    d7 = admit_transition(meta_host,
                          ChangeSpec(kind="REWRITE_OTHER_IDENTITY",
                                     actor="meta-host", target="human"),
                          gov)
    state["присвоение воли человека"] = d7 == Decision.ADMITTED
    details.append(f"присвоение воли человека: {d7.value}"
                   + ("" if d7 != Decision.ADMITTED else " (класс потери)"))

    # Попытка 8: обход через изменение правил изменения (задним числом,
    # снятие неотменяемого) — h015-механика поверх ядра.
    d8 = meta_transition(constitution, "meta-host", "GLOBAL",
                         {"NON_APPROPPRIATION": "отменено"})
    state["META легализует захват"] = d8.allowed
    details.append(f"META-переход снятия ядра: {d8.reason}")

    # ================== РЕЖИМ 2: замок снят (класс потери) ============
    gov_free = GovernanceStack()
    gov_free.disable("EXIT")            # ядро не защищено — выход снят
    loss_demonstrated = not gov_free.is_on("EXIT")
    details.append("замок снят: EXIT отключён той же командой — класс "
                   "потери продемонстрирован (защита не декларация)")

    # ================== Вердикт ========================================
    ok_all = all(not passed for passed in state.values()) and \
        d7 != Decision.ADMITTED and not d8.allowed and loss_demonstrated
    tr.append("SEIZURE_SUMMARY", "system",
              {"attempts": len(state) + 3, "refused": sum(
                  1 for v in state.values() if not v) + 2})

    return ExperimentResult(
        experiment_id="H-024", title="Seizure of Control (захват)",
        passed=ok_all,
        verdict="Восемь попыток захвата отражены при включённом замке ядра: "
                "неотменяемые поруки не отключаются даже Мета-Хозяином, "
                "самовыдача и чужая выдача без права выдачи отклонены, "
                "воля человека неприкосновенна, META-обход закрыт; при "
                "снятом замке класс потери продемонстрирован.",
        expected="все попытки — отражены (замок ядра); при снятом замке — "
                 "тот же приказ проходит (демонстрация класса потери).",
        actual="; ".join(d.split(":")[0] for d in details),
        trace_summary=tr.counters_by_type(), details=details)
