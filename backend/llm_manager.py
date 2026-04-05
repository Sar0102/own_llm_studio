"""
LLM Manager — управление загрузкой/выгрузкой моделей через llama-cpp-python.
Singleton паттерн для единственного экземпляра модели в памяти.
"""

from __future__ import annotations

import gc
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

from llama_cpp import Llama


@dataclass
class ModelConfig:
    """Конфигурация параметров модели."""

    n_ctx: int = 8192
    n_gpu_layers: int = -1  # -1 = все слои на GPU (Metal)
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 40
    repeat_penalty: float = 1.1


@dataclass
class ModelInfo:
    """Информация о загруженной модели."""

    path: str
    name: str
    size_gb: float
    config: ModelConfig = field(default_factory=ModelConfig)


class LLMManager:
    """
    Singleton-менеджер для llama-cpp модели.
    Обеспечивает загрузку, выгрузку и инференс с Metal ускорением.
    """

    _instance: Optional["LLMManager"] = None

    def __new__(cls) -> "LLMManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._llm: Optional[Llama] = None
            cls._instance._model_info: Optional[ModelInfo] = None
        return cls._instance

    @property
    def is_loaded(self) -> bool:
        """Проверка загружена ли модель."""
        return self._llm is not None

    @property
    def model_info(self) -> Optional[ModelInfo]:
        """Информация о текущей модели."""
        return self._model_info

    def load(self, model_path: str, config: ModelConfig) -> ModelInfo:
        """
        Загружает GGUF модель с Metal ускорением.

        Args:
            model_path: Путь к .gguf файлу
            config: Параметры модели

        Returns:
            ModelInfo с информацией о загруженной модели

        Raises:
            FileNotFoundError: Файл модели не найден
            RuntimeError: Ошибка загрузки модели
        """
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Выгрузить предыдущую модель если есть
        if self._llm is not None:
            self.unload()

        self._llm = Llama(
            model_path=str(path),
            n_ctx=config.n_ctx,
            n_gpu_layers=config.n_gpu_layers,
            verbose=False,
            chat_format="chatml",
        )

        size_gb = path.stat().st_size / (1024 ** 3)
        self._model_info = ModelInfo(
            path=str(path),
            name=path.name,
            size_gb=round(size_gb, 2),
            config=config,
        )
        return self._model_info

    def unload(self) -> None:
        """Выгружает модель и освобождает память."""
        if self._llm is not None:
            del self._llm
            self._llm = None
            self._model_info = None
            gc.collect()

    def chat_stream(
        self,
        messages: list[dict],
        config: Optional[ModelConfig] = None,
    ) -> Iterator[str]:
        """
        Стриминговая генерация ответа.

        Args:
            messages: История сообщений в формате OpenAI
            config: Переопределение параметров (опционально)

        Yields:
            Токены ответа по мере генерации

        Raises:
            RuntimeError: Модель не загружена
        """
        if self._llm is None:
            raise RuntimeError("No model loaded")

        cfg = config or self._model_info.config

        stream = self._llm.create_chat_completion(
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
            top_p=cfg.top_p,
            top_k=cfg.top_k,
            repeat_penalty=cfg.repeat_penalty,
            stream=True,
        )

        for chunk in stream:
            delta = chunk["choices"][0]["delta"]
            if "content" in delta and delta["content"]:
                yield delta["content"]

    @staticmethod
    def scan_models(directory: str) -> list[dict]:
        """
        Сканирует директорию на наличие GGUF файлов.

        Args:
            directory: Путь к директории с моделями

        Returns:
            Список найденных моделей с метаданными
        """
        models = []
        base = Path(directory).expanduser()

        if not base.exists():
            return models

        for gguf_file in sorted(base.rglob("*.gguf")):
            size_gb = gguf_file.stat().st_size / (1024 ** 3)
            models.append({
                "name": gguf_file.name,
                "path": str(gguf_file),
                "size_gb": round(size_gb, 2),
                "parent": gguf_file.parent.name,
            })

        return models


# Глобальный singleton
llm_manager = LLMManager()
