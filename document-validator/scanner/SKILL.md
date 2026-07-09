---
name: document-validator-scanner
description: Sensitive-data scanner for documentation resources. Receives ONE file from a resources/ folder (png/jpg/gif/svg/drawio, delivered as base64), checks it against the sensitive-data.md dictionary — vision analysis for raster images, decoded-XML text scan for drawio/svg — and writes CVAL-SENS issues to a JSON file. Never quotes the found sensitive values. Invoked by the document-validator-orchestrator.
---

# Document Validator — Sensitive Data Scanner

## Overview

Scans **one** file from a `resources/` folder for sensitive information. One scanner = one file
(изображение в base64 занимает большой объём контекста — поэтому строго по одному файлу и с
лимитом размера).

## Canonical sources

- **`../sensitive-data.md`** — словарь категорий (SD-01…SD-11), признаки, применимость
  (drawio/image), severity, замены. **Читай его первым**; сканируй строго по нему,
  не изобретай собственных категорий.
- **`../error-codes.md`** — шаблоны `CVAL-SENS` / `CVAL-SENS-SKIP` и правила плейсхолдеров.

## Input (from orchestrator)

| Param | Description |
|---|---|
| `file_path` | Repo-relative путь к файлу в `resources/` (remote) |
| `file_id` | Sanitized путь для имени выходного файла |
| `output_path` | `{workspace_path}/tmp/document-validator/scans/<file_id>.json` |

## Workflow

1. Read `../sensitive-data.md`.
2. **Size gate**: если размер файла известен до чтения и > 5 МБ (до base64) — не читай
   содержимое; эмить один `CVAL-SENS-SKIP` (INFO, причина: размер) и перейди к шагу 6.
3. **Read** the file via `get_single_file(file_path)` — единственный сетевой вызов;
   содержимое приходит в **base64**.
4. **Branch by type**:
   - **`.drawio` / `.svg`** (текстовые): декодируй base64 → XML. Для `.drawio`, если контент
     `<diagram>` дополнительно сжат (deflate+base64) — распакуй. Сканируй **текст** по всем
     категориям с колонкой `drawio`: домены/хосты SD-04, IP/ключи/хеши SD-05, пары
     логин—пароль SD-06, аббревиатуры SD-08…SD-11, ФИО/e-mail SD-01 и т.д. Это
     детерминированный паттерн-скан по признакам словаря — не интерпретируй смысл диаграммы
     сверх необходимого.
   - **Растровые** (`.png .jpg .jpeg .gif .bmp .webp`): визуальный анализ изображения по всем
     категориям с колонкой `image`: текст на скриншотах (адресные строки, вкладки, конфиги,
     логины/пароли, внутренние домены), лица/фото людей (SD-01), подписи на схемах,
     аббревиатуры. Осмотри изображение целиком, включая фон, вкладки браузера, док/панели ОС.
5. **Emit issues**: одна находка = одна категория в одном файле (несколько вхождений — одна
   находка с количеством). Код `CVAL-SENS`, severity — из таблицы категорий.
   **АБСОЛЮТНОЕ правило: не воспроизводить найденное значение** (ни пароль, ни IP, ни ФИО,
   ни домен целиком) ни в `message`, ни в `advice` — только категория + описание места
   словами (`location_hint`). Если тип файла не поддержан или декодирование не удалось —
   `CVAL-SENS-SKIP` (INFO, причина).
6. **Write** `output_path` (always, even with empty `issues`).

## Output

> **Все значения полей — строки; `null` остаётся `null`.**

```json
{
  "file": "documentation/documents/architecture/resources/deploy-scheme.png",
  "issues": [
    {
      "code": "CVAL-SENS",
      "severity": "ERROR",
      "path": "documentation/documents/architecture/resources/deploy-scheme.png",
      "message": "В файле `documentation/documents/architecture/resources/deploy-scheme.png` обнаружены признаки чувствительной информации: SD-04 — ссылки на внутренние ресурсы (2 вхождения), подписи узлов на схеме развертывания.",
      "position": null,
      "advice": "Заменить внутренние хосты на обезличенные имена узлов"
    }
  ]
}
```

Issue fields и severity levels — как в worker skill; `position` для изображений — `null`.

## Rules

1. One scanner = exactly one file; один вызов `get_single_file`; лимит 5 МБ.
2. Сканируй только по категориям `../sensitive-data.md`; учитывай исключения категорий
   (SD-08: «не в именах собственных» — применять буквально, имена продуктов не флаговать).
3. Никогда не цитируй найденные значения — категория + место словами.
4. `advice` — императив, одно действие, без воспроизведения значения; иначе `null`.
5. Always write `output_path` (empty `issues` if clean).
6. Все значения полей в JSON — строки; `null` остаётся `null`. Язык — русский,
   термины/ID категорий — как в словаре.
