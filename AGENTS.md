# Excalibur-2-Cloud Instructions

Язык: русский (тенант может сменить в `shared/tenant-config.json`).

## Первый запуск

Если `memory/setup/status.json` → `complete != true` **или**
`shared/tenant-config.json` → `setup_complete != true`:

→ работай как **`excalibur-blog-setup`** (skill `setup-excalibur-blog`).  
→ **Не** запускай Scout / Research / Publish.

См. `CLOUD-FIRST-RUN.md`, `SETUP.md`.

## Канон (после setup)

```text
Scout? → research_start → Research → Title → Writer(смысл)
→ Sol(слог) → Description(Дзен-карточка) → Cover-text || Schema → Cover
→ Indexer(llms) → Publish → Fixer → merge → Content-learner
```

**Writer** → `drafts/writer.html` (факты и смысл; статья под Дзен, не бриф).  
**Sol** (`excalibur-blog-sol`) → финальный `article.html` слогом тенанта
(`shared/SOUL.md` + `shared/soul-examples/`). Полный рерайт, не только лид.  
**Description** (`excalibur-blog-description`) → `description-brief.json`
(тизер карточки Дзена / RSS; `shared/dzen-description-rules.md`).  
≠ title, ≠ opening. После Description — stamp `pipeline_canon` + structural
checks (opening_meta, **sol_rewrite_depth**, description_gate, html_linter).
Прозу после Sol не переписывают (кроме возврата Sol при FAIL гейтов
слога / rewrite-depth; FAIL description → снова Description).

**Title** → `title-brief.json`.

Никто не читает уже опубликованные статьи сайта — только
`published-titles-only.md` / `shared/published-titles.md` для anti-dup
(заголовки **≤30 дней**). После publish папка
`memory/blog/articles/<topic>/` **удаляется** — никаких cover PNG /
article.html / research в долгосрочной памяти.

`memory/topics/` запрещена. Scout → handoff + `signal_urls` + Wordstat
(из tenant / site-brief).

```bash
python3 scripts/excalibur_blog_research_start.py --topic-id B111 --title "…"
```

## Cloud Automation

**UI prompt / cron / restore:** `CLOUD-AUTOMATION.md`.  
**Cost (HARD):** `shared/cloud-cost-rules.md` — **один** cloud-агент на весь
пайплайн; в Automation **запрещён** `Task(...)` (это отдельные VM). Роли =
skill-файлы в той же сессии. Одна статья/run; Fixer только при open incidents;
после publish — titles 30d + purge article_dir.  
Не заменять Agent Instructions на «Запусти плагин».

## Ошибка

- Второй автор / rewrite-loop **поверх Sol** (Sol — единственный стилевой рерайт)
- Термин-дамп / research-брифинг в открытии финала
- Description = title или обрезка лида (двойная карточка в Дзене)
- topics / SEO-хвосты
- Writer/Sol читают старые article.html / live-сайт как образец
- Хранение cover PNG / тел статей после publish (память = только title ≤30д)
- Publish без pipeline_canon stamp
- Scout/тема про RF-blocked heroes без Дзен-канона (если `dzen_rf_pack`)
- Sol выдумывает факты, которых нет в `drafts/writer.html` / research
- Sol подкрашивает только лид, оставляя тело Writer (rewrite-depth FAIL)
- Широкий обход репо / лишние Task в Cloud (см. cloud-cost-rules)
- Запуск пайплайна до завершения Setup

## Preflight

**До Scout (если dzen_rf_pack):** прочитать `shared/dzen-content-rules.md` +
`shared/rf-blocked-entities.json`.

```bash
python3 scripts/excalibur_blog_doctor.py
python3 scripts/excalibur_blog_today.py
python3 scripts/excalibur_blog_research_start.py --topic-id <id> --title "<short>"
```

Директор: `.cursor/agents/excalibur-blog-director.md` (не Task).  
Setup: `.cursor/agents/excalibur-blog-setup.md` (не Task).
