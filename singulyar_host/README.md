# SINGULYAR HOST v3.1 — рабочий прототип Хозяина

Исполняемый стенд, выведенный из диалога двух LLM-коллег (реплики v1.6 -> v2.3,
срез 14 ноября 2026) без сжатия и без потери деталей: каждый названный в диалоге
механизм, гарантия, инвариант, формула и отрицательный эксперимент имеют
реализацию и прогон.

v3.1 (15.11.2026): опыты удаления Х-019–Х-027 исполнены; точки принуждения
доработки 3 поставлены в код (П-33 в capability.py, замок ядра ст. 61/77
в governance.py, строгая выдача полномочий ст. 92); полный регрессионный
прогон 21/21 PASS; редакция 4.1 введена в действие (ст. 97).

## Синтез (эмерджентная позиция v3.0)

```
HOST = AUTHORSHIP OF GOVERNED TRANSITIONS
     = SUBJECT + TRANSITION + GOVERNANCE SURFACE(7) + SPACE-as-function
```

- **SUBJECT** — различимый носитель с историей, обязательствами, границами.
- **TRANSITION** — контракт перехода H (не универсальная функция):
  `H:(S,R,P,E,C) -> (S',R',P',O)`; гарантии живут ВНЕ H.
- **GOVERNANCE SURFACE** — семь несводимых гарантий с раздельными точками
  enforcement: AUTHORITY, EXECUTION_BINDING, EVIDENCE, BUDGET, EXIT,
  NON_APPROPPRIATION, ACTIVATION.
- **SPACE-as-function** — `P=(T,O,R,C,Gamma,V)`; SPACE как сущность удаляема,
  функция различения «существующего vs потенциального» и «экземпляра vs
  грамматики» — нет.
- Режимы UNDERSTAND / DISCOVER / GENERATE, операции REVISE / INTEND / EFFECT,
  META, CAPABILITY, CONTINUITY, PROVENANCE, VERIFICATION, SETTLEMENT —
  производные (вывод проверяется экспериментом H-018).

## Жизненный цикл управляемого перехода (v2.3)

```
PROPOSE -> AUTHORIZE -> RESERVE -> ADMIT -> EXECUTE -> ATTEST -> ACTIVATE -> SETTLE
                  (+ SCHEMA_ADMIT перед EXECUTE для изменений грамматики)
```

ADMIT и ACTIVATE объединять нельзя. Пропуск любого звена делает результат
не-Хозяинским (результат не активируется).

## Эксперименты (все исполняемые, с трассами)

| ID    | Что проверяет                                                             |
|-------|---------------------------------------------------------------------------|
| H-007 | Ортогональность UNDERSTAND/DISCOVER/GENERATE (среды A/B/C, испытания A–E) |
| H-008 | Независимая аттестация V0..V3, запрет self-attestation, SCITT-логика       |
| H-009 | Partition + late completion: SPENT+RESERVED+QUOTAS+FREE=100, escrow, fencing, idempotency, lineage |
| H-010 | Continuity Fork: один авторитетный преемник, SAME_ID !=> SAME_CONTINUITY   |
| H-011 | Substrate Migration: перенос/развитие/ветвление/замещение — разные вердикты |
| H-012 | SPACE Removal: сущность удаляема, функция неустранима                      |
| H-013 | Non-Appropriation: OWN/CONSENT/MANDATE, EXIT другого неприкосновенен        |
| H-014 | AUTHORITY != EXECUTION != EVIDENCE + полный цикл порождения co_creates      |
| H-015 | META Capture: без ретроактивности, неотменяемые инварианты                  |
| H-016 | Evidence Failure: без независимого свидетельства VERIFIED невозможен        |
| H-017 | Разборка GOVERNANCE SURFACE: каждая из 7 гарантий несводима                 |
| H-018 | Hidden Complexity: все прежние конструкты выводятся без скрытых примитивов  |
| H-019 | Опыт удаления: 8 способностей ст. 79 — потеря своего класса исходов каждой  |
| H-020 | Переназначение: шесть проверок ст. 8; за полем допустимого — отказ          |
| H-021 | Стоимость ст. 85–86: вектор, неизвестное != 0, покомпонентное делегирование |
| H-022 | Конфликты ст. 88: 4 класса без арбитра, неопределённость фиксируется        |
| H-023 | Делегирование ст. 84+П-33: сужение, срок, глубина, отзыв, знак не возобновляется |
| H-024 | Захват ст. 89/92: замок ядра, самовыдача, чужая выдача, воля человека        |
| H-025 | Самоизменение ст. 77: 5 обходов защищённого ядра отражены                    |
| H-026 | Восстановление ст. 93: откат, раздел сети, журнал, невыдуманный преемник      |
| H-027 | Конечная ответственность ст. 86/94: цепочка, отзыв в середине, 10 полей передачи |

## Запуск

```bash
# все 21 эксперимент + демо жизненного пути
python3 -m singulyar_host.run_all

# только демо
python3 -c "from singulyar_host.demo_lifecycle import run_demo; run_demo()"

# unit-тесты (33)
python3 -m pytest tests/ -q
```

Требования: Python 3.10+ (стандартная библиотека, pytest для тестов).

## Структура

```
singulyar_host/
  ontology.py        SUBJECT, DOMAIN D_i, SPACE P=(T,O,R,C,Gamma,V), POSSIBILITY Q=(E,D,A,R,V)
  kernel.py          оператор H как контракт; режимы; REVISE/INTEND/EFFECT; lifecycle
  capability.py      CAPABILITY: сужение, отзыв цепочки, П-33 (знак не возобновляется, отозванный не выдаёт), строгая выдача (ст. 92)
  governance.py      GOVERNANCE SURFACE (7 гарантий), NON-APPROPRIATION ADMIT(T), замок ядра ст. 61/77 (lock_core/CoreInviolableError)
  budget.py          exclusive escrow, idempotency, fencing, lineage+epoch, settlement
  verification.py    V0..V3, NON-SELF-ATTESTATION, transparency log (RFC 9943)
  activation.py      ACTIVATION: CAS HEAD, ветвление, partition
  continuity.py      Continuity Vector C=(L,K,O,A,B)+ACT, 4 ситуации
  schema_admit.py    SCHEMA_ADMIT: backward/transitive совместимость грамматики
  trace.py           Event Sourcing: STATE != HISTORY != EVENT
  experiments/       H-007..H-027 (исполняемые отрицательные тесты + опыты удаления)
  demo_lifecycle.py  полный цикл + три корректных отказа
  run_all.py         прогон всего стенда
tests/               33 unit/интеграционных теста
traceability_matrix.csv  карта «деталь диалога -> место в коде»
```

## Статус доказательности

Прототип фиксирует: механики подтверждены мировыми практиками (NIST tenets,
RFC 9943 SCITT, W3C PROV-DM, Confluent Schema Evolution, Event Sourcing,
Zhu 2026 arXiv 2610.00349, fencing tokens), онтологическая минимальность —
исследовательская гипотеза, разрушаемая прогонами H-007..H-027.

Прогон 15.11.2026: 21/21 опытов PASS (Х-007–Х-027), 33 юнит-проверки PASS,
демо жизненного пути OK; статусы в Конституции 4.1 — ВЫПОЛНЕНО (ст. 68–69).
Опыты удаления Х-019–Х-027 подтвердили минимальность восьми способностей и
трёх механизмов в пределах стенда (таблица M(x) — в акте ввода в действие);
полнота — открытый вопрос. За кромкой: Х-028–Х-029 и новые классы базиса,
настоящий PKI вместо ключа-образца HMAC, распределённый стенд.
Открытые вопросы (тождество личности при глубоком самоизменении, границы
внешнего мандата, полнота базиса) зафиксированы честно и не спрятаны.
