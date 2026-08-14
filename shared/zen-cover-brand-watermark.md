# Cover brand watermark (optional, tenant)

После Setup Visual тенант может включить бейдж канала на каждой панели
(cover + inline 01..03). Пока `cover_watermark.enabled` = false — скрипт
watermark **пропускает** шаг (не BLOCKER).

## Когда включено

1. Формат панели строго **16:9**.
2. Справа сверху: круглый аватар + текст handle из tenant-config
   (`cover_watermark.handle`, например `t.me/YOUR_CHANNEL`).
3. Аватар: путь `cover_watermark.avatar_path` (файл тенанта в `memory/cover/assets/`).
4. Не закрывать главный hook огромным бейджем — ширина ≈ 14–28% панели.

Конфиг: `shared/tenant-config.json` → `cover_watermark` и/или
`memory/cover/brand-telegram.json`.

## Вариативность

Cover-агент на каждый новый article **ротирует** фон и героя сцены.
Запрещено: одна и та же картинка железа в каждой статье.
Inline 2–4: только информативные схемы.
