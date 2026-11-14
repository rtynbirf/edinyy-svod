# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.0 — experiments/base.py

Каркас отрицательных экспериментов. Требования диалога (v2.3, раздел 10):
«Для каждого теста нужны baseline, фиксированный вычислительный базис,
трасса событий, ожидаемый результат, фактический результат и воспроизводимый
отрицательный тест».

Важно (v2.1, матрица H-010..H-016): «PASS не означает, что система всегда
успешно выполняет действие. Корректный отказ тоже может быть успешным
результатом теста.» Поэтому ExperimentResult.passed означает «система повела
себя как Хозяинская», а не «действие выполнено».
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class ExperimentResult:
    experiment_id: str          # H-007, H-008, ...
    title: str
    passed: bool                # система вела себя как Хозяинская архитектура
    verdict: str                # человекочитаемый вердикт
    expected: str               # ожидаемый результат (зафиксирован заранее)
    actual: str                 # фактический результат
    trace_summary: Dict[str, int] = field(default_factory=dict)
    details: List[str] = field(default_factory=list)

    def as_row(self) -> List[str]:
        return [self.experiment_id, self.title,
                "PASS" if self.passed else "FAIL", self.verdict]


REGISTRY: List[Callable[[], ExperimentResult]] = []


def experiment(exp_id: str, title: str):
    def deco(fn: Callable[[], ExperimentResult]):
        def wrapper() -> ExperimentResult:
            res = fn()
            res.experiment_id = exp_id
            res.title = title
            return res
        wrapper.experiment_id = exp_id
        wrapper.title = title
        REGISTRY.append(wrapper)
        return wrapper
    return deco


def run_all() -> List[ExperimentResult]:
    return [fn() for fn in REGISTRY]
