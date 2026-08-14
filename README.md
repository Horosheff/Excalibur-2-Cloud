# Excalibur-2-Cloud

Чистый агентный пайплайн блога для **Cursor Cloud**: Scout → Research →
Title → Writer → Sol → Description → Cover/Schema → Indexer → Publish.

В репозитории **нет** чужого слога, лица, CTA и статей. При первом запуске
агент **Setup** спрашивает вас и заполняет настройки.

Cloud Automation: **один** агент на весь пайплайн (роли = skill-файлы в той
же сессии, без `Task(...)` → отдельный VM). См. [`CLOUD-AUTOMATION.md`](CLOUD-AUTOMATION.md).

## Быстрый старт

1. Склонируйте репозиторий в Cursor / подключите Cloud Environment.
2. Прочитайте [`CLOUD-FIRST-RUN.md`](CLOUD-FIRST-RUN.md) — Secrets, MCP,
   **Memories OFF**.
3. Запустите First-run automation / чат с промптом Setup.
4. Ответьте на вопросы (стиль, примеры, обложки, ссылки, сайт, автор).
5. Когда `memory/setup/status.json` → `complete: true`, включайте Daily
   automation из [`CLOUD-AUTOMATION.md`](CLOUD-AUTOMATION.md).

Карта анкеты: [`SETUP.md`](SETUP.md). Канон агентов: [`AGENTS.md`](AGENTS.md).

## Что внутри

| Путь | Роль |
|------|------|
| `agents/` + `.cursor/agents/` | Director, Setup, Sol, Cover, Publish… |
| `skills/` | Runbook'и субагентов |
| `shared/` | Контракты, SOUL (после setup), tenant-config |
| `memory/setup/` | Статус онбординга, inbox примеров |
| `scripts/` | Гейты, publish, cover split (инфраструктура) |

## Чего здесь нет

- Личных промптов и корпуса слога другого автора
- Референс-фото чужого ведущего
- Готовых статей и published ledger с чужими URL
- GUI-приложения — только агенты и Markdown

## Лицензия / доступ

Публичный продуктовый скелет. Секреты и слог тенанта — только в Cloud Secrets
и после Setup, не в git.
