# Excalibur BLOG — Cloud cost rules

Жёсткие правила для Cursor Cloud Automation.

## Главное (почему были «миллионы токенов»)

В Cloud Automation инструмент `Task(excalibur-blog-*)` / `task_v2` поднимает
**отдельный cloud-агент (VM)** на каждую роль. В UI это Trigger=**Subagent**
каждые 1–4 минуты. Это НЕ «субагент внутри того же запуска плагина».

**Правильно:** один оркестратор на весь пайплайн. Роли = skill-файлы,
выполняемые в той же сессии.

## HARD

1. **Одна статья / один Automation-run / один cloud VM.**
2. **Запрещено** `Task(...)`, `Task(excalibur-blog-*)`, `task_v2`, `/in-cloud`
   в Cloud Automation.
3. Не вызывать `Task(excalibur-blog-director)`.
4. Роль выполняй так: Read `skills/<role>/SKILL.md` + `agents/excalibur-blog-<role>.md`
   → сделай работу сам → commit при необходимости → следующий шаг.
5. Не читать чужие `article.html`, live-сайт, `llms-full.txt` целиком, весь
   `memory/blog`, `memory/topics/`.
6. Anti-dup = `shared/published-titles.md` (published, ≤30 дней).
7. Fixer: сначала `rg '^status: open' memory/pipeline-fix-queue.md` —
   если пусто, не делай fixer-проход.
8. После publish+merge:
   `published_titles.py --days 30` + `memory_purge.py --drop-topic <ID>`.
9. doctor + today — один раз в начале.
10. Игнорировать stale Automation Memory / старый swarm.

## UI

- Промпт только из `CLOUD-AUTOMATION.md`.
- Cron рекомендуемый: `0 10 * * *`.
- Security review / Agent approval — OFF.
