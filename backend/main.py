"""
LLM Studio Backend — FastAPI сервер для локального запуска LLM моделей.
Замена LM Studio с поддержкой llama-cpp-python + Metal (Apple Silicon).
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from llm_manager import LLMManager, ModelConfig, llm_manager
from chat_store import init_db, session_repo, settings_repo, Session, Settings
from context_manager import context_manager


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="LLM Studio API",
    description="Local LLM inference server with Metal acceleration",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализируем БД при старте
init_db()

# Папка с фронтендом
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class LoadModelRequest(BaseModel):
    """Запрос на загрузку модели."""
    path: str = Field(..., description="Путь к .gguf файлу")
    n_ctx: int = Field(8192, ge=512, le=131072)
    n_gpu_layers: int = Field(-1, ge=-1)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=64, le=16384)
    top_p: float = Field(0.95, ge=0.0, le=1.0)
    top_k: int = Field(40, ge=1, le=200)
    repeat_penalty: float = Field(1.1, ge=1.0, le=2.0)


class ChatMessage(BaseModel):
    """Сообщение в чате."""
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    """Запрос к чату."""
    messages: list[ChatMessage]
    session_id: Optional[str] = None          # для загрузки истории из БД
    system_prompt: Optional[str] = None       # system prompt из UI
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=64, le=16384)
    stream: bool = True


class ScanRequest(BaseModel):
    """Запрос на сканирование папки."""
    directory: str = Field(default="~/Library/Application Support/LM Studio/models")


class CreateSessionRequest(BaseModel):
    """Создание новой сессии."""
    id: str
    title: str = "New chat"


class AppendMessagesRequest(BaseModel):
    """Сохранение сообщений пачкой после генерации."""
    session_id: str
    messages: list[ChatMessage]   # user + assistant


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Отдаём фронтенд."""
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"status": "LLM Studio API running", "docs": "/docs"}


@app.get("/api/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "model_loaded": llm_manager.is_loaded,
        "model": llm_manager.model_info.name if llm_manager.is_loaded else None,
    }


# ─── Settings routes ──────────────────────────────────────────────────────────

class UpdateSettingsRequest(BaseModel):
    """Запрос на обновление настроек."""
    models_dir:     Optional[str]   = None
    n_ctx:          Optional[int]   = Field(None, ge=512, le=131072)
    n_gpu_layers:   Optional[int]   = Field(None, ge=-1)
    temperature:    Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens:     Optional[int]   = Field(None, ge=64, le=16384)
    top_p:          Optional[float] = Field(None, ge=0.0, le=1.0)
    top_k:          Optional[int]   = Field(None, ge=1, le=200)
    repeat_penalty: Optional[float] = Field(None, ge=1.0, le=2.0)
    system_prompt:  Optional[str]   = None


@app.get("/api/settings")
async def get_settings():
    """Возвращает текущие настройки из БД."""
    loop = asyncio.get_event_loop()
    s = await loop.run_in_executor(None, settings_repo.load)
    return s.to_dict()


@app.put("/api/settings")
async def update_settings(req: UpdateSettingsRequest):
    """
    Обновляет настройки — только переданные поля.
    Остальные остаются без изменений.
    """
    loop = asyncio.get_event_loop()

    # Загружаем текущие
    current = await loop.run_in_executor(None, settings_repo.load)

    # Применяем только переданные поля
    updated = Settings(
        models_dir    = req.models_dir     if req.models_dir     is not None else current.models_dir,
        n_ctx         = req.n_ctx          if req.n_ctx          is not None else current.n_ctx,
        n_gpu_layers  = req.n_gpu_layers   if req.n_gpu_layers   is not None else current.n_gpu_layers,
        temperature   = req.temperature    if req.temperature    is not None else current.temperature,
        max_tokens    = req.max_tokens     if req.max_tokens     is not None else current.max_tokens,
        top_p         = req.top_p          if req.top_p          is not None else current.top_p,
        top_k         = req.top_k          if req.top_k          is not None else current.top_k,
        repeat_penalty= req.repeat_penalty if req.repeat_penalty is not None else current.repeat_penalty,
        system_prompt = req.system_prompt  if req.system_prompt  is not None else current.system_prompt,
    )

    await loop.run_in_executor(None, settings_repo.save, updated)
    return updated.to_dict()


# ─── Session routes ───────────────────────────────────────────────────────────

@app.get("/api/sessions")
async def list_sessions():
    """Список всех сессий без сообщений."""
    loop = asyncio.get_event_loop()
    sessions = await loop.run_in_executor(None, session_repo.list_sessions)
    return {
        "sessions": [
            {"id": s.id, "title": s.title, "created_at": s.created_at, "updated_at": s.updated_at}
            for s in sessions
        ]
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Сессия со всеми сообщениями."""
    loop = asyncio.get_event_loop()
    session = await loop.run_in_executor(None, session_repo.get_session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": [
            {"role": m.role, "content": m.content}
            for m in session.messages
        ],
    }


@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest):
    """Создаёт новую пустую сессию."""
    loop = asyncio.get_event_loop()
    session = await loop.run_in_executor(
        None, session_repo.create_session, req.id, req.title
    )
    return {"id": session.id, "title": session.title}


@app.post("/api/sessions/{session_id}/messages")
async def append_messages(session_id: str, req: AppendMessagesRequest):
    """
    Сохраняет пачку сообщений (user + assistant) после завершения генерации.
    Обновляет title сессии по первому user-сообщению.
    """
    loop = asyncio.get_event_loop()

    def _save():
        for m in req.messages:
            session_repo.append_message(session_id, m.role, m.content)
        session_repo.update_session_title_from_messages(session_id)

    await loop.run_in_executor(None, _save)
    return {"saved": len(req.messages)}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Удаляет сессию и все её сообщения."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, session_repo.delete_session, session_id)
    return {"deleted": session_id}


@app.get("/api/models/status")
async def model_status():
    """Статус загруженной модели."""
    if not llm_manager.is_loaded:
        return {"loaded": False}

    info = llm_manager.model_info
    return {
        "loaded": True,
        "name": info.name,
        "path": info.path,
        "size_gb": info.size_gb,
        "config": {
            "n_ctx": info.config.n_ctx,
            "n_gpu_layers": info.config.n_gpu_layers,
            "temperature": info.config.temperature,
            "max_tokens": info.config.max_tokens,
        },
    }


@app.post("/api/models/scan")
async def scan_models(req: ScanRequest):
    """
    Сканирует директорию на наличие GGUF файлов.
    По умолчанию смотрит в папку LM Studio.
    """
    models = llm_manager.scan_models(req.directory)
    return {"models": models, "count": len(models)}


@app.post("/api/models/load")
async def load_model(req: LoadModelRequest):
    """Загружает GGUF модель с заданными параметрами."""
    try:
        config = ModelConfig(
            n_ctx=req.n_ctx,
            n_gpu_layers=req.n_gpu_layers,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            top_p=req.top_p,
            top_k=req.top_k,
            repeat_penalty=req.repeat_penalty,
        )
        info = llm_manager.load(req.path, config)
        return {
            "success": True,
            "name": info.name,
            "size_gb": info.size_gb,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Load failed: {str(e)}")


@app.post("/api/models/unload")
async def unload_model():
    """Выгружает текущую модель из памяти."""
    if not llm_manager.is_loaded:
        raise HTTPException(status_code=400, detail="No model loaded")
    llm_manager.unload()
    return {"success": True}


import threading

# ─── Active generation registry ───────────────────────────────────────────────
# session_id → threading.Event (set = отмена)
_active_generations: dict[str, threading.Event] = {}


@app.post("/api/chat/cancel/{session_id}")
async def cancel_generation(session_id: str):
    """
    Отменяет активную генерацию для сессии.
    Вызывается фронтендом при beforeunload или нажатии кнопки ■.
    Частичный ответ будет сохранён в БД автоматически.
    """
    event = _active_generations.get(session_id)
    if event:
        event.set()
        return {"cancelled": True}
    return {"cancelled": False}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Стриминговый чат с моделью через SSE.
    Загружает полную историю из БД → оптимизирует контекст → стримит ответ.

    При разрыве соединения (перезагрузка страницы, закрытие вкладки):
    - Генерация останавливается через cancel_event
    - Частичный ответ сохраняется в БД
    """
    if not llm_manager.is_loaded:
        raise HTTPException(status_code=400, detail="No model loaded. Load a model first.")

    loop = asyncio.get_event_loop()

    # 1. Загружаем полную историю из БД если есть session_id
    existing_summary = ""
    db_messages = []
    if req.session_id:
        def _load():
            session = session_repo.get_session(req.session_id)
            summary = session_repo.get_summary(req.session_id)
            return session, summary

        session, existing_summary = await loop.run_in_executor(None, _load)
        if session:
            db_messages = session.messages

    # 2. Если истории в БД нет — используем messages из запроса (fallback)
    all_messages = db_messages if db_messages else [
        type("M", (), {"role": m.role, "content": m.content})()
        for m in req.messages
    ]

    # 3. Оптимизируем контекст через ContextManager
    n_ctx = llm_manager.model_info.config.n_ctx if llm_manager.is_loaded else 8192
    ctx_result = context_manager.build(
        messages=all_messages,
        system_prompt=req.system_prompt or "",
        existing_summary=existing_summary,
        n_ctx=n_ctx,
    )

    optimized_messages = ctx_result.messages

    # 4. Если summary обновился — сохраняем в БД асинхронно
    if ctx_result.new_summary and req.session_id:
        await loop.run_in_executor(
            None,
            session_repo.update_summary,
            req.session_id,
            ctx_result.new_summary,
        )

    # 5. Переопределение параметров из запроса
    override_config = None
    if req.temperature is not None or req.max_tokens is not None:
        base = llm_manager.model_info.config
        override_config = ModelConfig(
            n_ctx=base.n_ctx,
            n_gpu_layers=base.n_gpu_layers,
            temperature=req.temperature or base.temperature,
            max_tokens=req.max_tokens or base.max_tokens,
            top_p=base.top_p,
            top_k=base.top_k,
            repeat_penalty=base.repeat_penalty,
        )

    # 6. Cancel event — один на сессию
    session_id = req.session_id
    cancel_event = threading.Event()
    if session_id:
        _active_generations[session_id] = cancel_event

    # user_text — последнее user-сообщение для сохранения пары в БД
    user_text = next(
        (m["content"] for m in reversed(optimized_messages) if m["role"] == "user"),
        "",
    )

    async def token_generator():
        """
        Генератор токенов для SSE стриминга.

        Буферизует накопленный ответ и сохраняет его в БД в блоке finally —
        это гарантирует сохранение при любом исходе:
        полный ответ, отмена пользователем, разрыв соединения (перезагрузка).
        """
        response_buffer: list[str] = []
        completed = False

        # Отправляем мета-инфо о контексте фронтенду
        meta = {
            "type": "context_info",
            "total_tokens": ctx_result.total_tokens,
            "was_compressed": ctx_result.was_compressed,
            "trimmed_count": ctx_result.trimmed_count,
        }
        yield f"data: {json.dumps(meta)}\n\n"

        queue: asyncio.Queue = asyncio.Queue()
        curr_loop = asyncio.get_event_loop()

        def run_inference():
            """Инференс в отдельном потоке — проверяет cancel_event на каждом токене."""
            try:
                for token in llm_manager.chat_stream(optimized_messages, override_config):
                    if cancel_event.is_set():
                        break
                    curr_loop.call_soon_threadsafe(queue.put_nowait, token)
            except Exception as e:
                curr_loop.call_soon_threadsafe(queue.put_nowait, Exception(str(e)))
            finally:
                curr_loop.call_soon_threadsafe(queue.put_nowait, None)

        curr_loop.run_in_executor(None, run_inference)

        try:
            while True:
                item = await queue.get()
                if item is None:
                    completed = True
                    yield "data: [DONE]\n\n"
                    break
                if isinstance(item, Exception):
                    yield f"data: {json.dumps({'error': str(item)})}\n\n"
                    break
                response_buffer.append(item)
                yield f"data: {json.dumps({'token': item})}\n\n"

        except GeneratorExit:
            # Клиент закрыл соединение (перезагрузка / закрытие вкладки)
            cancel_event.set()

        finally:
            # Снимаем регистрацию
            if session_id:
                _active_generations.pop(session_id, None)

            # Сохраняем накопленный ответ в БД если есть что сохранять
            partial = "".join(response_buffer)
            if partial and session_id and user_text:
                suffix = "" if completed else " [прервано]"

                def _save_partial():
                    session_repo.append_message(session_id, "user",      user_text)
                    session_repo.append_message(session_id, "assistant", partial + suffix)
                    session_repo.update_session_title_from_messages(session_id)

                # run_in_executor недоступен в finally генератора — используем синхронный вызов
                try:
                    _save_partial()
                except Exception:
                    pass

    if req.stream:
        return StreamingResponse(
            token_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming fallback
    tokens = list(llm_manager.chat_stream(optimized_messages, override_config))
    return {"content": "".join(tokens)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
