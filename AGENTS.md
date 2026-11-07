# AGENTS.md

Instructions for AI coding agents working in this repository.

## Project overview

Автономная HTML-экспозиция «ЕДИНЫЙ СВОД»: весь архив аккаунта `rtynbirf`
(37 репозиториев) сведён в один файл — каталог, классификация по 8 кластерам,
конституционный слой, программы, инварианты, дыры. Ноль внешних запросов:
5 гарнитур зашиты base64 woff2 (подрезка pyftsubset по символам документа).
Правила аккаунта — в `rtynbirf/repo-doctrine`.

## Commands

Верификация пломб: `sha256sum -c SHA256SUMS.txt` (GNU).
Полная пересборка: `python3 build/build_svod.py` (идемпотентна, бит-в-бит).
Самопроверка данных: `python3 build/catalog_data.py`.
Резерв артефактов: `edinyy-svod.zip` (deflate -9).

## Conventions

- Keep changes minimal and focused; one logical change per commit.
- Never commit secrets, tokens, or credentials.
- Аддитивность: добавлять можно, удалять и переписывать — нельзя (доктрина, раздел 02).
- Артефакт генерируется: правки текста — только через `build/svod_content.py` /
  `build/catalog_data.py` с пересборкой; руками в HTML не править.
- После любых изменений — `SHA256SUMS.txt` + паспорт README (размер, sha256).
- Числа каталога (37/17/20, даты, языки) сверять с живым GitHub API перед правкой.
- Раздел XII «Дыры и тени» — живой реестр: закрывать дыры дельтами, не ретушировать.
