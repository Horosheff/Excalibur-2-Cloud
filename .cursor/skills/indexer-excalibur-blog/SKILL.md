---
name: indexer-excalibur-blog
description: Excalibur BLOG Indexer — llms.txt from titles (+ optional current article); no historical bodies.
---

# Indexer — titles-only (+ current)

Долгосрочная память = `shared/published-titles.md` (заголовки ≤30 дней).
Исторические `memory/blog/articles/*/article.html` и cover PNG **не**
сканируем и не храним.

```bash
# Default canon: titles ledger + optional current article body for llms-full
python3 scripts/excalibur_blog_llms_generator.py \
  --mode titles+current \
  --titles shared/published-titles.md \
  --article-dir memory/blog/articles/<topic_id>-<slug> \
  --blog-path / \
  --out-dir memory/blog

# Refresh titles window first (if needed)
python3 scripts/excalibur_blog_published_titles.py --days 30
```

Пиши `{{SITE_BASE}}` / `{{SITE_HOST}}` в git-артефакты. Не передавай живой
`PUBLIC_SITE_URL` в `--site-base` для commit.

Выход: `memory/blog/llms.txt` (titles index), `llms-full.txt` (только
текущая статья, если передана; иначе stub без исторических тел).
Без promotion-checklist, без правок `article.html`, без interlink.
