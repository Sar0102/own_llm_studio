


.PHONY: help install run run-stream run-local sync mcp api dev fmt lint test clean

# показывает доступные команды
help:
	@echo "Доступные команды:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## установить зависимости и сам пакет
	uv sync
	uv pip install -e .

# ============ CLI ============

run: ## запустить агента (q="..." [skill="..."])
	uv run agent-service run --query "$(q)" $(if $(skill),--skill $(skill))

run-stream: ## запустить со стримингом (q="...")
	uv run agent-service run --query "$(q)" $(if $(skill),--skill $(skill)) --stream

run-local: ## запустить без синхронизации скиллов из git
	uv run agent-service run --query "$(q)" $(if $(skill),--skill $(skill)) --no-sync

run-debug: ## запустить с подробными логами
	uv run agent-service run --query "$(q)" $(if $(skill),--skill $(skill)) --debug

# ============ Server ============

api: ## запустить FastAPI сервер
	uv run uvicorn agent_service.presentation.api.app:app --host 0.0.0.0 --port 8000 --reload

mcp: ## запустить MCP сервер
	uv run agent-service-mcp

# ============ Dev ============

fmt: ## отформатировать код
	uv run ruff format .
	uv run ruff check --fix .

lint: ## проверить код
	uv run ruff check .
	uv run mypy agent_service

test: ## прогнать тесты
	uv run pytest

clean: ## удалить кэш и склонированные скиллы
	rm -rf .skills .ruff_cache .mypy_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +




# короткий запуск
make run q="Generate release notes for v1.2.0"

# с конкретным скиллом
make run q="Release notes" skill=relnote-writer

# стрим
make run-stream q="Long task"

# локально без git
make run-local q="Test query"

# отладка
make run-debug q="Debug this"

# запустить API
make api

# запустить MCP
make mcp

# форматирование
make fmt

# подсказка
make help
