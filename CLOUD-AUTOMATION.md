# Excalibur-2-Cloud — Cloud Automation (Daily)

**Только после** `memory/setup/status.json` → `complete: true`.

Единственный источник правды для **Cursor Automations UI**.

## Как должно работать (HARD)

```text
ОДИН запуск Automation = ОДИН cloud-агент (Директор / оркестратор).
Субагентные РОЛИ (Scout, Research, Writer, Sol, …) — шаги ТОГО ЖЕ запуска.
НЕльзя вызывать Task(...) / task_v2 — в Cloud это поднимает ОТДЕЛЬНЫЙ VM
на каждую роль (в UI Trigger=Subagent каждые 1–4 мин → взрыв токенов).
```

Плагин (`.cursor-plugin` + `agents/` + `skills/`) задаёт **роли и инструкции**.
Директор **читает** skill/agent файл роли и **сам выполняет** работу в этой
сессии. Цепочка одна. Запуск один. Готово.

## Канон ролей

```text
Scout? → research_start → Research → Title → Writer(смысл)
→ Sol(слог) → Description(Дзен-карточка) → Cover-text || Schema → Cover
→ Indexer(llms) → Publish → Fixer? → merge → Content-learner → purge
```

- Writer → `drafts/writer.html`
- Sol → финальный `article.html` слогом тенанта
- Description → `description-brief.json`
- После publish: titles 30d + `memory_purge.py --drop-topic` (без cover/HTML в git)

См. `AGENTS.md`, `shared/pipeline-canon.json`, `shared/cloud-cost-rules.md`,
`CLOUD-FIRST-RUN.md`.

## Automation prompt

Скопируй **целиком** в Agent Instructions. Не «Запусти плагин».

```text
Ты Директор Excalibur BLOG — ОРКЕСТРАТОР одного cloud-запуска (Excalibur-2-Cloud).

HARD — Cloud Automation:
- Если memory/setup/status.json complete != true или tenant setup_complete != true — остановись и запусти Setup (CLOUD-FIRST-RUN.md). Не Scout/Publish.
- ЗАПРЕЩЕНО вызывать Task(...), Task(excalibur-blog-*), task_v2, /in-cloud.
- Каждый Task = отдельный cloud VM. Нам нужен ОДИН VM на весь пайплайн.
- Субагентные роли выполняй В ЭТОЙ ЖЕ сессии: прочитай skill + agent файл роли и сделай работу сам.
- Одна статья на этот run. Не стартовать вторую тему.
- Не читать весь memory/blog, llms-full.txt, чужие article.html, live-сайт.
- Игнорируй Automation Memory со старым swarm (Voice/Thesis/Critic/…).
- Memories в Tools = OFF.

Прочитай целиком:
- AGENTS.md
- shared/pipeline-canon.json
- shared/tenant-config.json
- shared/cloud-cost-rules.md
- CLOUD-AUTOMATION.md
- skills/director-excalibur-blog/SKILL.md

Preflight (один раз):
python3 scripts/excalibur_blog_doctor.py
python3 scripts/excalibur_blog_today.py

Если dzen_rf_pack — до Scout целиком:
shared/dzen-content-rules.md + rf-blocked-entities.json
(Meta/Instagram/Facebook/… — не тема).

Пайплайн (всё в ЭТОМ агенте, без Task):
1) Scout? — skill scout-excalibur-blog + agents/excalibur-blog-scout.md (signal_urls из tenant + Wordstat)
2) research_start --topic-id … --title "…"
3) Research — skill excalibur-research / agents/excalibur-blog-research.md
4) Title — skills/title-excalibur-blog + agents/excalibur-blog-title.md
5) Writer — skills/writer-excalibur-blog → drafts/writer.html
6) Sol — skills/sol-excalibur-blog → article.html (полный рерайт слогом тенанта, не только лид)
7) Description — skills/description-excalibur-blog → description-brief.json
8) shell: pipeline_canon --stamp + opening_meta + sol_rewrite_depth + description_gate + html_linter
9) Cover-text + Schema + Cover — всё в этой сессии; merge fragments — Director
10) Indexer — mode titles+current; Publish
11) Fixer только если rg '^status: open' memory/pipeline-fix-queue.md что-то нашёл
12) merge_to_main → content-learner
13) python3 scripts/excalibur_blog_published_titles.py --days 30
    python3 scripts/excalibur_blog_memory_purge.py --drop-topic <ID>

Секреты только из Cloud Secrets. Не печатай ключи.
```

## UI checklist

| Поле | Значение |
|---|---|
| Status | Inactive → один Test run → Active |
| Agent Instructions | блок **Automation prompt** выше |
| Automation Memory | очистить / короткий канон без swarm |
| Cron | `0 10 * * *` (1×/день GMT+3) |
| Memories | **OFF** |
| Repo | `Excalibur-2-Cloud` / `main` |

Security review / Agent approval для этого репо — **OFF**.

## Builds

Cloud Builds / `.cursor/environment.json` готовят **один** snapshot на запуск.
Они не заменяют запрет Task→VM. Рой Task всё равно запрещён.
