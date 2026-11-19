# -*- coding: utf-8 -*-
"""
SINGULYAR HOST v3.3 — run_all.py
Прогон всех экспериментов Х-007..Х-066 с таблицей вердиктов.
Х-061..Х-066 — фронт X (автоматность): автомат дома как конечный автомат
(8 состояний-статусов, полная таблица переходов, именованные запреты).
Запуск:  python -m singulyar_host.run_all
"""
from __future__ import annotations

import json
import sys
from typing import List

from . import demo_lifecycle
from .experiments import base

# Импортируем модули экспериментов — декораторы регистрируют их в REGISTRY.
from .experiments import (  # noqa: F401
    h007_orthogonality,
    h008_attestation,
    h009_partition,
    h010_h011_continuity,
    h012_space,
    h013_non_appropriation,
    h014_authority_possibility,
    h015_meta_capture,
    h016_evidence_failure,
    h017_guarantee_independence,
    h018_hidden_complexity,
    h019_eight_abilities,
    h020_reassignment,
    h021_cost_vector,
    h022_conflict,
    h023_delegation,
    h024_seizure,
    h025_self_modification,
    h026_recovery,
    h027_responsibility,
    h030_h032_revocation,
    h033_h035_core_attacks,
    h036_h040_statuses,
    h041_h045_attestation,
    h046_h050_minimality,
    h051_h055_history,
    h056_h060_reserve,
    h061_h066_automaton,
)


def main(export_path: str = "") -> int:
    print("=" * 100)
    print("SINGULYAR HOST v3.3 — рабочий прототип Хозяина. Срез: 19 ноября 2026.")
    print("Фронт X (автоматность): 8 состояний-статусов, 12 событий, "
          "96/96 клеток таблицы переходов")
    print("Ядро: SUBJECT + TRANSITION + GOVERNANCE SURFACE(7) + SPACE-as-function")
    print("HOST = AUTHORSHIP OF GOVERNED TRANSITIONS")
    print("=" * 100)

    results = base.run_all()
    widths = (10, 62, 7)
    print(f"{'ID':<{widths[0]}} {'Эксперимент':<{widths[1]}} {'Вердикт':<{widths[2]}}")
    print("-" * 100)
    all_pass = True
    for r in results:
        all_pass = all_pass and r.passed
        verdict = "PASS" if r.passed else "FAIL"
        print(f"{r.experiment_id:<{widths[0]}} {r.title:<{widths[1]}} {verdict:<{widths[2]}}")
    print("-" * 100)
    print(f"ИТОГО: {sum(1 for r in results if r.passed)}/{len(results)} PASS; "
          f"общий вердикт: {'ЯДРО ДЕРЖИТСЯ' if all_pass else 'ЕСТЬ ПРОКОЛЫ'}")

    if export_path:
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump([{
                "id": r.experiment_id, "title": r.title, "passed": r.passed,
                "verdict": r.verdict, "expected": r.expected,
                "actual": r.actual, "details": r.details,
                "trace_summary": r.trace_summary,
            } for r in results], f, ensure_ascii=False, indent=2)
        print(f"Результаты экспортированы: {export_path}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    export = sys.argv[1] if len(sys.argv) > 1 else ""
    demo_lifecycle.run_demo(verbose=True)
    print()
    sys.exit(main(export_path=export))
