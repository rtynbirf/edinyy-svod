# -*- coding: utf-8 -*-
"""Каталог 41 репозитория аккаунта rtynbirf.

Источник: GitHub API GET /user/repos (снимок 2026-11-08, волна W-AUD-06) + карта аккаунта
rtynbirf/repo-doctrine/06-карта-аккаунта.md (снимок 2026-11-01 и приложения
до 2026-11-07). Каждая строка сверена с живым API-ответом; флаги archived/fork
проверены отдельно; судьба пяти форков из карты TH-GH-10 проверена
GET-ом (HTTP 404 — удалены Хозяином после аудита 2026-11-06).

Ревизия 2026-11-08 (раунд 3, мультиагент ПОЛИМАТ): сверка с живым API —
39 репозиториев. Удалены: windows-encyclopedia, windows-full-report
(поглощены каноном windows-chronicle), призрак H-PE11. Добавлены:
cell-rs, release-vault, markitdown, edinyy-svod, polimat-hub.
"""

# (имя, видимость, язык, дата создания ГГГГ-ММ-ДД, кластер, род в своде)
CATALOG = [
    ("cell65-host", "публ", "JavaScript", "2026-09-30", "G",
     "антицензурный комплекс: PAC, MV3-расширение, sovereign-node, 2FA-автомат"),
    ("singulyar", "публ", "HTML", "2026-10-01", "F",
     "офлайн-вселенная караоке RUVSON: 64 песни × 200 языков, PWA"),
    ("singulyar-llm", "публ", "Python", "2026-10-02", "F",
     "локальная LLM СИНГУЛЯРА: Qwen2.5-0.5B GGUF, генерация в браузере"),
    ("polymath-os", "публ", "Python", "2026-10-16", "C",
     "суверенная медиа-ОС: 5 слоёв, SINGULYAR EIR v0.6, 35 ADR, 290 тестов"),
    ("H-PE11-PHOENIX", "прив", "PowerShell", "2026-10-20", "G",
     "ворклог операций TH-* и сборки WinPE PHOENIX-11"),
    ("rumu", "публ", "—", "2026-10-20", "F",
     "СИНГУЛЯР РУМУ: стриминг BL/GL, P2P + автопилот; АРХИВ по карте"),
    ("rtynbirf.github.io", "публ", "HTML", "2026-10-24", "E",
     "сайт-профиль: MEGA-PLAYER SINGULYAR, офлайн-плеер"),
    ("global-video-platforms-registry", "публ", "Python", "2026-10-25", "F",
     "верифицированный реестр 1071 видеоплатформы (1032 активных)"),
    ("voice-atlas-llm", "публ", "Python", "2026-10-26", "F",
     "Атлас-LLM: модель-эксперт по клонированию голоса, LoRA + RAG"),
    ("ruvson-lyrics", "прив", "JavaScript", "2026-10-27", "F",
     "тексты 65 треков RUVSON: черновики, пайплайн, финальный ZIP"),
    ("ruvson-rse2", "публ", "Python", "2026-10-28", "F",
     "RSE-2: станок одной песни, шаги 0–6, голос RUVSON"),
    ("karaoke-dream", "публ", "JavaScript", "2026-10-28", "F",
     "браузерное караоке: неон, гид-вокал, Зелёный коридор тональности"),
    ("os-forge", "публ", "Shell", "2026-10-28", "G",
     "автономный батник: карта среды → сеть пунктов → готовый ISO"),
    ("nous", "прив", "Shell", "2026-10-28", "A",
     "НОУС: конституция для человека и агентов, ТЗ форжа ISO"),
    ("windows-chronicle", "прив", "JavaScript", "2026-10-30", "H",
     "полная хроника Windows 1985–2026: версии, боли, продвижение"),
    ("repo-doctrine", "прив", "—", "2026-10-31", "A",
     "доктрина репозиториев: правила игры для Хозяина и агентов"),
    ("github-runbook", "прив", "—", "2026-10-31", "A",
     "ранбук GitHub: все флаги Settings, ветки, API-шпаргалка"),
    ("commons", "публ", "Python", "2026-11-01", "C",
     "один организм из открытых проектов: геном-спеки, синапсы MCP"),
    ("domovoy-tweaker", "публ", "PowerShell", "2026-11-01", "G",
     "ДОМОВОЙ: твикер как состояние — журнал, дрифт-страж, undo"),
    ("polymath-atlas-v107", "публ", "Lean", "2026-11-04", "C",
     "Lean 4: честный evidence-audit фреймворк (прототип, не теорем-проверитель)"),
    ("neutral-browser", "публ", "Rust", "2026-11-04", "G",
     "браузерный движок с нуля: HTML→DOM→CSS→STYLE→LAYOUT→PAINT→PNG"),
    ("uace-pml", "прив", "JavaScript", "2026-11-04", "D",
     "UACE × PML: экспортёр AI-чатов, Evidence First, PML-STRUCT canon"),
    ("task-graph-propagator", "прив", "Python", "2026-11-04", "C",
     "один пропагатор — все функции структуры графа задач (полукольца, Кана)"),
    ("rent-mechanism-q43", "прив", "Python", "2026-11-04", "B",
     "рента-программа R11–R49: ядро Q43 v2, законы L1–L6, инвариант I_K″"),
    ("red-thread-debt-audit", "прив", "Python", "2026-11-04", "B",
     "КРАСНАЯ НИТЬ: аудит суверенного долга, канон v8.0, матрица 230×17"),
    ("cell-swarm", "публ", "Python", "2026-11-04", "C",
     "РОЙ: клетка, окно, указатели, храповик, семя"),
    ("polimat-task174", "прив", "Python", "2026-11-04", "B",
     "ПОЛИМАТ · TASK174: проверка канона по строкам, пломбы, ловушки, Б25.8"),
    ("polymath-tools-atlas", "публ", "HTML", "2026-11-05", "D",
     "каталог 665 AI-инструментов по контракту ГОЛОГРАММА v1"),
    (".github", "публ", "—", "2026-11-06", "A",
     "дефолтные community-файлы аккаунта: формы, шаблоны, кодексы"),
    ("agryp", "публ", "C", "2026-11-06", "C",
     "PID1-подобный супервизор AI-агентов: один файл C, файл-как-API"),
    ("runtime-protocol", "публ", "Python", "2026-11-06", "C",
     "клетка роя: уравнение ρ̇, GENESIS_EXEC, VOLATILE_META, CANCER_FILTER"),
    ("web-evolution-1991-2026", "прив", "HTML", "2026-11-06", "E",
     "эволюция Веба 1991→2026: 5 эпох, таймлайн, WCAG+APCA, 267 КБ"),
    ("language-through-the-ages", "прив", "HTML", "2026-11-06", "E",
     "язык сквозь эпохи: 7 способов мыслить язык, 7 эпох × 7 гарнитур"),
    ("universal-agent", "публ", "Python", "2026-11-06", "C",
     "UniversalAgent (TsUA): один мозг, замкнутый контур, 4 слоя памяти"),
    ("cell-rs", "публ", "Rust", "2026-11-07", "C",
     "первая Rust-клетка роя: контур сверки, sha256-пломбы, кросс-тесты с Python-ядром"),
    ("release-vault", "публ", "—", "2026-11-07", "G",
     "шифрованный офсайт-архив релизных ассетов приватных репо (AES-256-CBC/PBKDF2)"),
    ("markitdown", "публ", "Python", "2026-11-07", "D",
     "форк Microsoft markitdown: конвертер документов в Markdown для конвейеров"),
    ("edinyy-svod", "прив", "HTML", "2026-11-07", "E",
     "единый свод архива: автономная HTML-экспозиция каталога (сам этот артефакт)"),
    ("polimat-hub", "прив", "Python", "2026-11-07", "A",
     "место сверок мультиагента ПОЛИМАТ: архитектура, журнал операций, stdlib-инструменты, vault/"),
    ("polymath-gen", "публ", "Python", "2026-11-07", "C",
     "медиа-агент роя: задание человека → промпт → изображение/видео → самокритика; CI, dependabot, паспорт со счётчиком LLM-прогонов"),
    ("rtynbirf", "публ", "Python", "2026-11-07", "E",
     "живой профиль аккаунта: числа не пишутся руками, генерируются скриптом (П-02)"),

]

CLUSTERS = [
    ("A", "Конституции и доктрины",
     "правила игры для человека и агентов: конституция, доктрина, ранбук, community-файлы",
     ["nous", "repo-doctrine", "github-runbook", ".github"]),
    ("B", "Программы-исследования",
     "знание только с пломбой: вердикт-рамки, пре-регистрация, чужаки-приёмщики",
     ["red-thread-debt-audit", "rent-mechanism-q43", "polimat-task174"]),
    ("C", "Полимат-инженерия",
     "агенты, рой, супервизоры, графы и организм из открытых проектов",
     ["polymath-os", "cell-swarm", "runtime-protocol", "universal-agent",
      "agryp", "task-graph-propagator", "commons", "polymath-atlas-v107",
      "polymath-gen"]),
    ("D", "Инструменты-приборы",
     "каталоги и экспортёры, где доказательство = воспроизводимая выдача",
     ["polymath-tools-atlas", "uace-pml"]),
    ("E", "Экспозиции",
     "автономные HTML-эссе: один файл, ноль внешних запросов",
     ["web-evolution-1991-2026", "language-through-the-ages", "rtynbirf.github.io",
      "rtynbirf"]),
    ("F", "Медиа-вселенная РУВСОН",
     "караоке, голос, тексты, стриминг и реестр платформ — суверенно, без корпораций",
     ["singulyar", "singulyar-llm", "rumu", "ruvson-lyrics", "ruvson-rse2",
      "karaoke-dream", "global-video-platforms-registry", "voice-atlas-llm"]),
    ("G", "Суверенная инфраструктура",
     "антицензурный комплекс, форж ОС, твикер, браузер и оперативная память работ",
     ["cell65-host", "os-forge", "domovoy-tweaker", "neutral-browser",
      "H-PE11-PHOENIX", "H-PE11"]),
    ("H", "Windows-хроника",
     "одна тема, канон: хроника 1985→2026 (два зеркала поглощены 2026-11-08)",
     ["windows-chronicle", "windows-full-report", "windows-encyclopedia"]),
]

# Факты-константы свода (сверены API 2026-11-08, волна W-AUD-06)
FACTS = {
    "total": 41,
    "private": 15,
    "public": 26,
    "first_repo": "cell65-host",
    "first_date": "2026-09-30",
    "last_date": "2026-11-08",
    "archived": [],
    "map_ghost_forks": ["langchain", "n8n-docs", "ui", "winget-pkgs"],
    "stars": {"voice-atlas-llm": 1, "universal-agent": 1},
}

if __name__ == "__main__":
    names = {r[0] for r in CATALOG}
    cluster_members = [m for _, _, _, ms in CLUSTERS for m in ms]
    assert len(CATALOG) == FACTS["total"], len(CATALOG)
    assert len(names) == len(CATALOG), "дубликаты имён"
    assert names == set(cluster_members), (
        set(names) ^ set(cluster_members))
    priv = sum(1 for r in CATALOG if r[1] == "прив")
    assert priv == FACTS["private"], priv
    print("каталог: %d репо, кластеры %d, приватных %d — согласовано"
          % (len(CATALOG), len(CLUSTERS), priv))
