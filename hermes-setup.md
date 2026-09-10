# Hermes Agent — установка и настройка

Инструкция под корпоративное окружение с TLS-инспекцией и self-hosted LLM за LiteLLM-прокси.

---

## 1. Установка

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Проверить, куда встал venv (понадобится дальше):

```bash
cat $(which hermes)
```

Обёртка укажет на интерпретатор, обычно `~/hermes/hermes-agent/venv/bin/python`.

---

## 2. Подключение своего провайдера

### Интерактивно

```bash
hermes model
# → Custom endpoint (self-hosted / VLLM / etc.)
# → base URL, API key, имя модели
```

### Вручную — `~/.hermes/config.yaml`

```yaml
providers:
  work:
    api: https://services.test.sbt/eliza/openai/v1
    key_env: CORP_API_KEY
    transport: chat_completions
model:
  default: Qwen/Qwen3.6-27B
  provider: custom:work
  context_length: 64000
```

Ключ — в `~/.hermes/.env`:

```
CORP_API_KEY=...
```

**Важно:**

- Минимум контекста — 64 000 токенов, иначе конфиг отклоняется на старте.
- Секреты держать в `.env`, не инлайном в `config.yaml`.
- Для SSO-гейтвеев с протухающими токенами вместо `api_key` использовать `key_cmd` — команду, печатающую токен.

---

## 3. Проблема: `SSL: CERTIFICATE_VERIFY_FAILED`

### Причина

Корпоративный TLS-инспектирующий прокси подписывает трафик своим CA, которого нет в хранилище Python.

### Что НЕ работает

- `ssl_ca_cert` в конфиге провайдера — числится в документации, но это открытый feature request (issue #48440). `_build_keepalive_http_client()` создаёт `httpx.HTTPTransport` с `verify=True` и пользовательский CA не читает.
- `SSL_CERT_FILE` — не пробрасывается в `httpx.HTTPTransport` при кастомном транспорте.
- `PYTHONHTTPSVERIFY=0` — влияет только на `urllib`/`http.client`, httpx его не смотрит. Плюс отключает проверку глобально, что небезопасно.

### Рабочее решение — CA в certifi нужного venv

```bash
# 1. Путь к certifi venv-а Hermes (не системного python!)
CERTIFI=$(~/hermes/hermes-agent/venv/bin/python -c 'import certifi; print(certifi.where())')
ls -l "$CERTIFI"

# 2. Резервная копия
cp "$CERTIFI" "$CERTIFI.bak"

# 3. Проверить формат сертификата — должно быть PEM
head -1 /path/to/sbertech_chain_ca.pem
# ожидается: -----BEGIN CERTIFICATE-----

# 4. Дописать
cat /path/to/sbertech_chain_ca.pem >> "$CERTIFI"
tail -1 "$CERTIFI"

# 5. Проверить
~/hermes/hermes-agent/venv/bin/python -c \
  "import httpx; print(httpx.get('https://ВАШ_ХОСТ/v1/models').status_code)"
```

Любой HTTP-код в ответ (200/400/401) = TLS починен. Откат: `cp "$CERTIFI.bak" "$CERTIFI"`.

> ⚠️ `certifi` перезаписывается при `pip install -U certifi` и обновлениях Hermes — держи `.pem` в постоянном месте и повторяй шаг 4 после апдейтов.

### Если сертификата нет под рукой

```bash
openssl s_client -connect ВАШ_ХОСТ:443 -showcerts </dev/null 2>/dev/null \
  | awk '/BEGIN CERT/,/END CERT/' > /tmp/chain.pem
```

---

## 4. Проблема: `HTTP 400 UnsupportedParamsError: reasoning_effort`

LiteLLM не принимает `reasoning_effort` для моделей, которые его не поддерживают.

**На стороне Hermes:**

```bash
hermes config set agent.reasoning_effort none
```

**На стороне LiteLLM** (предпочтительно, если прокси свой — закроет проблему для всех клиентов):

```yaml
litellm_settings:
  drop_params: true
```

---

## 5. MCP-серверы

### Из каталога

```bash
hermes mcp                 # интерактивный пикер
hermes mcp catalog         # текстовый список
hermes mcp install <name>  # по имени
hermes mcp configure <name>  # изменить набор тулов позже
hermes mcp login <name>      # OAuth-авторизация
```

### Свой сервер — CLI

```bash
# HTTP
hermes mcp add svc_ai_agent --url http://localhost:8000/mcp

# stdio
hermes mcp add svc_ai_agent --command python --args -m svc_ai_agent.mcp
```

### Свой сервер — `~/.hermes/config.yaml`

```yaml
mcp_servers:
  svc_ai_agent:
    url: "http://localhost:8000/mcp"
    headers:
      X-User-Id: "sarvar"
    tools:
      include: [validate_document, get_graph]
    supports_parallel_tool_calls: true
```

**Обязателен ровно один ключ:** `url` (HTTP) или `command` (stdio). Всё остальное опционально, включая `include` — без него регистрируются все тулы.

Полезные ключи:

| Ключ | Смысл |
|---|---|
| `enabled: false` | пропустить сервер, не подключаться |
| `timeout` / `connect_timeout` | таймаут вызова тула / подключения |
| `supports_parallel_tool_calls` | параллельный запуск тулов сервера |
| `client_cert` / `client_key` | mTLS |
| `tools.exclude` | обратная логика: всё, кроме перечисленного |
| `sampling.enabled: false` | запретить серверу просить инференс |

Тулы регистрируются как `mcp_<server>_<tool>`.

### Применить

```
/reload-mcp
```

**Подводные камни:**

- Для stdio env не наследуется из шелла — только явный `env` плюс безопасный baseline.
- OAuth во время работающей сессии: автоперезагрузка даёт 30 сек, этого мало. Добавь запись, затем `hermes mcp login <server>` из отдельного терминала (ждёт 5 минут).
- HTTP предпочтительнее stdio, если сервис уже поднят — stdio плодит второй инстанс со своим пулом коннектов к БД.

---

## 6. Скиллы

### Свой скилл — просто директория

```
~/.hermes/skills/<категория>/<имя>/SKILL.md
```

```bash
mkdir -p ~/.hermes/skills/software-development/doc-validation
```

`SKILL.md`:

```markdown
---
name: doc-validation
description: Валидация документации в svc-ai-agent — когда применять
version: 1.0.0
---

## When to Use
## Procedure
## Pitfalls
## Verification
```

Скопировать готовый: `cp -a /path/to/my-skill ~/.hermes/skills/software-development/`

### Установка чужих

```bash
npx skills add <owner>/<repo>       # формат agentskills.io
hermes skills tap add <owner>/<repo>  # репозиторий как tap, для команды
hermes skills list
```

### Дать Hermes создать скилл самому

```
/learn <путь|URL>
```

Или словами: «сохрани этот подход как скилл». Триггеры автосоздания: задача в 5+ вызовов тулов, восстановление из ошибки, поправка пользователя.

**Как формулировать:** сначала решить задачу вместе с агентом, потом дистиллировать. Явно проговорить: когда применять (идёт в `description`), что было граблями, как проверить результат.

### Применить

Новые сессии — автоматически. Текущая — `/reset` (или `--now` для немедленного сброса кеша промпта).

**Что важно:**

- Прогрессивная загрузка: Level 0 — метаданные всех скиллов (~3000 токенов), Level 1 — полный `SKILL.md`, Level 2 — файлы из директории. Поэтому `description` критичен, а тяжёлые справочники выносить в соседние файлы.
- Приоритет при совпадении имён: project → local (`~/.hermes/skills/`) → external_dirs. Скилл в репозитории перебивает глобальный и едет вместе с кодом.
- Curator раз в 7 дней архивирует **автосозданные** скиллы после 30/90 дней простоя. Написанные вручную не трогает.

---

## 7. Свои команды

### Скилл = слеш-команда автоматически

```
/doc-validation проверь docs/api
/doc-validation                    # агент сам спросит, что нужно
```

Это штатный способ сохранить длинный промпт. Строковые prompt-шорткаты как quick commands **не поддерживаются**.

### Quick commands — шелл и алиасы

```yaml
quick_commands:
  status:
    type: shell
    command: "docker compose ps"
  deploy:
    type: shell
    command: "make deploy"
```

Выполняются мгновенно, без обращения к LLM. Работают только в CLI — гейтвеи и cron игнорируют. `type: alias` указывает на существующую слеш-команду.

### Бандлы — несколько скиллов разом

```yaml
bundles:
  validation:
    - doc-validation
    - graph-checks
```

---

## 8. Диагностика

```bash
hermes doctor                  # ключи, провайдеры, MCP, бэкенды
cat ~/.hermes/logs/errors.log  # секреты вырезаны
hermes config get              # текущий конфиг
```

Расшифровка типовых ошибок:

| Симптом | Причина |
|---|---|
| Нет HTTP-кода вообще | не дошло до провайдера: сеть, TLS, таймаут |
| `CERTIFICATE_VERIFY_FAILED` | см. раздел 3 |
| 401 | ключ не подхватился, проверь `key_env` |
| 404 / unknown model | ID модели не совпадает с каталогом провайдера |
| 400 `UnsupportedParamsError` | см. раздел 4 |
| Connection refused | сервер не поднят, не тот порт, слушает только `127.0.0.1` |
| Unknown provider | опечатка в `provider: custom:<name>` |

---

## 9. Удаление

```bash
hermes uninstall          # агент, данные остаются
hermes uninstall --full   # плюс config, чаты, секреты
hermes uninstall --gui    # только десктоп-приложение
```

Остатки после `--full` — известный баг, проверить вручную:

```bash
find "$HOME/Library" "$HOME/.local" "$HOME/.config" "$HOME/.cache" \
  -maxdepth 3 -iname 'hermes' 2>/dev/null
```

Отдельно: `hermes gateway uninstall`, а также долгоживущие контейнеры —

```bash
docker ps -a --filter label=hermes-agent=1
```
