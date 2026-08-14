---
description: Excalibur-2-Cloud — живой прогон статьи через оркестратор.
---

# Excalibur-2-Cloud — запуск пайплайна

Сначала: `memory/setup/status.json` → `complete: true`. Иначе — Setup.

«Запусти Excalibur для темы **B01**»

## Параметры

- `topic_id`: B01 | all | P0-only
- `publish`: yes | no (default yes)

## Пайплайн (human-first-v2)

```text
Scout? → Research → Title → Writer → Sol → Description
→ Cover||Schema → Indexer (llms-only) → Publish (auto)
→ Fixer → merge → Content-learner → purge
```

- **Writer** → `drafts/writer.html` (смысл / статья под Дзен).
- **Sol** → финальный `article.html` слогом тенанта (полный рерайт).
- **Description** → `description-brief.json` (Дзен/RSS карточка).
- Тела старых статей и live-сайт не открывать.
- Publish BLOCK без setup / без pipeline_canon stamp.

Cloud UI / cost: `CLOUD-AUTOMATION.md` + `shared/cloud-cost-rules.md`.

## Оркестратор

Директор — основной агент чата (не Task в Cloud). Сценарий:
[skills/director-excalibur-blog/SKILL.md](../skills/director-excalibur-blog/SKILL.md).

Handoff runtime: `.cursor/excalibur-blog-handoff.md`
