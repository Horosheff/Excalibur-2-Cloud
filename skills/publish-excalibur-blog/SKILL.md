---
name: publish-excalibur-blog
description: Excalibur BLOG Publish — WP post, featured image, inline images, schema meta, ledger и post-publish.
---

# Excalibur BLOG — Publish (субагент ⑥)

## Future publish hard gate

До upload проверь `article.meta.json.theme_blocks`: faq, quiz и side_stickers
= `skip`; в body ровно один тематический FAQ. После upload обязательно
запусти `excalibur_blog_live_page_gate.py` по
`shared/live-page-contract.md`. Только live-page-report PASS разрешает
publish PASS/PIPELINE DONE.

**Live FAQ vs wptexturize (B71 / INC-20260721-1655):** если live FAQ
parity FAIL только из‑за `--` ↔ em dash (`—` / `&#8212;`) — это WP
`wptexturize`, не ошибка schema. Gate нормализует тире; **не** переписывай
`schema.jsonld` / FAQ HTML ради texturize. Сначала сверь local schema ↔
article FAQ; при чистом dash-only mismatch — обнови/перезапусти live gate.

**Live FAQ vs backslashes (B78 / INC-20260723-1254):** bootstrap PHP обязан
`wp_slash` title/content/excerpt перед `wp_insert_post`/`wp_update_post`
(и финальный update после inline src). Без этого literal `\` в Windows paths
пропадает из visible FAQ, а FAQPage JSON-LD (meta + `wp_slash`) сохраняет →
false live FAQ BLOCK. Не вырезай backslashes из body, чтобы «починить» gate.

**Live FAQ H2 (B74 / INC-20260722-1248):** visible FAQ detector =
`html_linter.is_faq_section_heading` (bare `FAQ` / «Частые вопросы» /
openers). Канон в article — `<h2>Частые вопросы</h2>`; bare FAQ больше не
ломает live count vs FAQPage.

**Роль:** `Task(excalibur-blog-publish)`  
**Когда:** сразу после Indexer (шаг ⑤), когда QA PASS, cover, schema и indexer готовы.

## Агент знает (это твоя зона, не «скрипт вместо тебя»)

Это **агентская** система: ты читаешь контракт и **сам** принимаешь решения. Скрипты — инструменты (загрузка, проверка), они не заменяют знание роли.

Ты обязан понимать и проверять:

1. **Live URL постов = `/{slug}/`**, не `/blog/{slug}/`. После Indexer в HTML не должно быть `href="/blog/..."`.
2. **Media Library в WP** для каждой картинки (cover + inline):
   - **Атрибут alt** — осмысленный русский текст из registry / `<img alt>`
   - **Подпись (caption)** — осмысленный alt; deprecated `meme_caption_ru` игнорировать
   - **Описание (description)** — alt (+ контекст H2 для inline)
   - В dry-run смотри `cover_media` / `inline_media` — все флаги должны быть `true`. Если `false` — чини registry/HTML **до** publish, не надейся что «скрипт додумает».
3. После GEO/Indexer сам перезапусти `link_verify` если HTML менялся.
4. **`llms.txt` на live** — после publish задеплой (`excalibur_blog_llms_deploy.py` или `--deploy-llms`), если Indexer обновил файлы.
5. Скрипт может **подстраховать** (не пустить без QA PASS / не считать WARN медиа успехом) — это safety net, не отмена твоей ответственности.

## Контракт

`shared/excalibur-wp-publish-contract.md`

## Preconditions (все обязательны)

| Проверка | Файл / env |
|----------|------------|
| QA PASS | `article-qa.md` → plain `verdict: PASS` (не `**verdict:**`) |
| Links | `link-verify.json` → pass |
| Cover | `cover/cover.png` + alt в `cover-registry.json` |
| Schema | `schema.jsonld` |
| Content evidence | optional/legacy; missing → SKIP (не Publish BLOCK) |
| Freshness | `freshness-report.json` → PASS |
| Pipeline canon | `pipeline_canon=human-first-v1`, `editorial_swarm=false` |
| Credentials | `FTP_HOST`/`FTP_USER`/`FTP_PASS`/`FTP_ROOT=.` + `PUBLIC_SITE_URL` |
| Allow flag | `EXCALIBUR_BLOG_ALLOW_PUBLISH=yes` |

**Агент знает:** пароль FTP = пароль SFTP. Сразу SFTP с `FTP_*`; не требуй отдельный `SSH_PASS`, если задан `FTP_PASS`. Root = `.` (login cwd).

Если allow flag ≠ yes → **`❌ PUBLISH BLOCKER`** (не silent skip).

### MEDIA REFRESH (уже опубликованный пост)

Когда нужно только перезалить cover/inline на live-пост (cover hotfix, stamp ban),
а `freshness-report.json` = **STALE** из‑за правки watched contracts после QA:

```bash
# link-verify свежий PASS обязателен
python3 scripts/excalibur_blog_link_verify.py \
  memory/blog/articles/<topic_id>-<slug>/article.html \
  -o memory/blog/articles/<topic_id>-<slug>/link-verify.json \
  --site-base "$PUBLIC_SITE_URL"

python3 scripts/excalibur_blog_wp_publish.py \
  --article-dir memory/blog/articles/<topic_id>-<slug> \
  --media-refresh --dry-run

python3 scripts/excalibur_blog_wp_publish.py \
  --article-dir memory/blog/articles/<topic_id>-<slug> \
  --media-refresh
```

`--media-refresh` требует:
- ledger `status=published` для `topic_id`;
- `article-qa.md` PASS, `link-verify.json` pass, cover/schema/evidence;
- `pipeline_canon=human-first-v1`;
- допускает только freshness **STALE** (не FAIL/BLOCK);
- **не** эквивалент `--skip-gates`.

Алиас только для freshness: `--allow-stale-freshness` (без проверки ledger published).
Не комбинируй с `--skip-gates`.

## Алгоритм

### 0. Theme contract (идемпотентно)

```bash
python3 scripts/excalibur_blog_theme_contract_deploy.py --deploy
```

Скрипт делает backup и учит тему уважать future-only meta-флаги. Без этого
live-page gate после upload заблокирует generic FAQ/quiz/stickers.

### 1. Preflight publish

```bash
python3 scripts/excalibur_blog_link_verify.py \
  memory/blog/articles/<topic_id>-<slug>/article.html \
  -o memory/blog/articles/<topic_id>-<slug>/link-verify.json \
  --site-base "$PUBLIC_SITE_URL"
```

Gate: `link-verify.json` → pass. Иначе FIX (writer/QA) или BLOCKER.

`link-verify.py` проверяет HTTP по живому `--site-base`/`PUBLIC_SITE_URL`, но файл `-o` всегда git-safe: internal `url`/`checked_url` с `{{SITE_BASE}}`, не live host и не `[REDACTED]`.

Soft social hosts (`t.me` / `telegram.me` / `wa.me` / `vk.com`): DNS/resolver errors (`Name or service not known`, `errno -2`, `getaddrinfo`, unreachable) и timeouts → warning + `ok: true`, **не** FAIL. Cloud часто без DNS к Telegram — не BLOCKER и не удаляй `t.me` из статьи из‑за soft flake (INC-20260713-2014).

### 2. Env-check

```bash
python3 scripts/excalibur_blog_wp_publish.py --env-check
```

Проверяет allow flag, public URL и SFTP-переменные без вывода секретов. Для ad-hoc Python-проверок не импортируй `excalibur_blog_wp_publish.py` из корня без `scripts/` в `sys.path`; безопаснее использовать этот CLI.

### 3. Dry-run

```bash
python3 scripts/excalibur_blog_wp_publish.py \
  --article-dir memory/blog/articles/<topic_id>-<slug> \
  --dry-run
```

Проверь: slug, title, размер PHP payload без ошибок.

### SITE_BASE expand (secret-scan)

Indexer/schema/cover **must** leave `{{SITE_BASE}}` in committed artifacts (not live host, not `[REDACTED]`):
`schema.jsonld`, llms, `link-verify.json`, `cover/quad-mcp-batch.json`, `wp-publish-result.json`.

`excalibur_blog_wp_publish.py` expands `{{SITE_BASE}}` → `PUBLIC_SITE_URL` **at publish time only** in `load_article` (content + schema meta payload).
On-disk artifacts stay with the placeholder. Dry-run fails if `schema_placeholder_remaining` after expand (missing `PUBLIC_SITE_URL`/`--public-base`).
After publish, `wp-publish-result.json` is written with live host already redacted to `{{SITE_BASE}}` (permalink + raw_output).
Ledger (`shared/published-articles.md`) writes path-only `/slug/` via `ledger_url_for_commit`.

### 4. Publish

```bash
python3 scripts/excalibur_blog_wp_publish.py \
  --article-dir memory/blog/articles/<topic_id>-<slug>
```

Скрипт:
- грузит bootstrap сразу через **SFTP/SSH** (порт 22 по умолчанию), без FTP-попытки;
- если настроенный `SSH_ROOT`/`FTP_ROOT` возвращает SFTP ENOENT до upload, один раз пробует `.` и пишет warning без раскрытия секретов; после такого warning лучше обновить Cloud Secret root на `.`;
- **ты** проверяешь preflight; скрипт — safety net; media refresh live-поста → `--media-refresh` (не `--skip-gates`); emergency-only: `--skip-gates`;
- создаёт/обновляет WP post;
- загружает featured image и пишет Media Library meta: **alt**, **подпись (caption)**, **описание (description)**, title — из текстов Cover/HTML, которые ты уже проверил;
- загружает **все локальные inline `<img>`**, пишет те же media meta и подменяет `src` на WP media URL;
- не засчитает WARN медиа / неполный upload как успех;
- пишет post meta `_excalibur_blog_schema_jsonld`;
- по твоей команде `--deploy-llms` → SFTP `llms.txt` + `llms-full.txt` в корень WP.

Dry-run: **агент читает** `cover_media` / `inline_media` — все флаги `true`, иначе чини registry/HTML до publish.

### 5. Cloud WebFetch Fallback

Если локальный HTTP-триггер bootstrap упал (timeout / WinError 10060):

1. Скрипт печатает `=== FALLBACK_TRIGGER_URL ===` с URL `excalibur-blog-publish-once.php`.
2. Cloud-агент открывает URL через WebFetch и пишет ответ в `memory/webfetch-response.txt`.
3. Скрипт продолжает и читает ответ из файла.

**Не останавливайся** на первом timeout — используй fallback.

### 6. Post-publish артефакты

| Файл | Действие |
|------|----------|
| `wp-publish-result.json` | создаёт скрипт (verdict pass/fail) |
| `memory/blog/wp-publish-log.md` | допиши секцию с post_id, permalink, inline ids |
| `shared/published-articles.md` | если есть строка topic_id со status=in_progress — обнови date/url/status=published; иначе добавь строку |
| `memory/pipeline-fix-queue.md` | если дописал incident — **закоммить** вместе с ledger/publish artifacts; канон только `pipeline-fix-queue.md` (не `pipeline-incident-queue.md`) |
| handoff | блок `=== EXCALIBUR BLOG PUBLISH ===` + permalink в `PIPELINE DONE` |

### 7. Post-publish

Interlinker удалён. Не добавляй inbound-ссылки из старых статей.
Опционально: deploy llms (`--deploy-llms` / `excalibur_blog_llms_deploy.py`).

**Titles-only memory (HARD):** после PASS publish (и обычно после merge)
обнови ledger заголовков и **удали** локальный `article_dir` — не оставляй
cover PNG / HTML / research в git:

```bash
python3 scripts/excalibur_blog_published_titles.py --days 30
python3 scripts/excalibur_blog_memory_purge.py --drop-topic <topic_id>
```

Долгосрочная память = только строки title в `shared/published-titles.md`
(окно 30 дней).

## Handoff block (шаблон)

```text
=== EXCALIBUR BLOG PUBLISH ===
topic_id:
slug:
article_dir:
publish_date:
verdict: PASS|FAIL
permalink:
post_id:
featured_image:
inline_images:
schema_meta: ok|fail
blockers:
```

## Blockers

- `❌ PUBLISH BLOCKER` — QA не PASS, link-verify fail, нет cover/schema, credentials, allow flag
- `❌ PUBLISH FAIL` — скрипт вернул fail (смотри `raw_output` в wp-publish-result.json)
- Freshness STALE на **первой** публикации → перезапусти named hard roles / freshness; не `--skip-gates`
- Freshness STALE на **media refresh** уже published → `--media-refresh` (QA/link-verify остаются)

## Запрещено

- Писать или переписывать longread
- Генерировать cover/schema с нуля
- Пропускать dry-run
- Использовать `--skip-gates` для media refresh (INC-20260723-1235)
- Завершать пайплайн без записи или обновления `published-articles.md` при успешном publish
