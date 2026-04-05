"""
Context Manager — гибридная оптимизация контекста для локальных LLM.

Стратегия (Hybrid):
  1. System prompt          — всегда целиком, первым
  2. Summary старой истории — сжатые пары Q→A которые не влезли
  3. Последние сообщения    — целиком, с конца, пока влезает бюджет
  4. Сообщения режутся ТОЛЬКО по границам — никогда не посередине

Обновление summary:
  После каждого ответа бэкенд проверяет — если какие-то сообщения
  были вытолканы из окна, они добавляются в summary как пары Q→A.
  Summary хранится в sessions.summary в SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ─── Constants ────────────────────────────────────────────────────────────────

# Какую долю n_ctx оставляем под генерацию ответа
RESPONSE_RESERVE = 0.20

# Сколько последних сообщений гарантированно сохраняем целиком
MIN_RECENT_MESSAGES = 4

# Максимальная длина одной пары в summary (символов)
SUMMARY_PAIR_LENGTH = 120


# ─── Models ───────────────────────────────────────────────────────────────────

@dataclass
class ContextResult:
    """Результат оптимизации контекста."""
    messages: list[dict]          # готово для передачи в LLM
    total_tokens: int             # оценка токенов
    was_compressed: bool          # был ли контекст сжат
    trimmed_count: int            # сколько сообщений ушло в summary
    new_summary: Optional[str]    # обновлённый summary (если изменился)


# ─── ContextManager ───────────────────────────────────────────────────────────

class ContextManager:
    """
    Строит оптимизированный контекст для LLM из полной истории сообщений.

    Гарантии:
    - Сообщения никогда не обрезаются посередине
    - Последние MIN_RECENT_MESSAGES сообщений всегда включаются целиком
    - System prompt всегда присутствует и идёт первым
    - Summary хранит осмысленные пары Q→A, не обрывки
    """

    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Быстрая оценка токенов без тяжёлых зависимостей.
        Эвристика: 1 токен ≈ 4 символа (достаточно для большинства языков).
        """
        return max(1, len(text) // 4)

    def build(
        self,
        messages: list,           # Message объекты из БД (role, content)
        system_prompt: str = "",
        existing_summary: str = "",
        n_ctx: int = 8192,
    ) -> ContextResult:
        """
        Строит оптимизированный список сообщений для передачи в LLM.

        Args:
            messages:         Полная история из БД (Message dataclass или dict)
            system_prompt:    System prompt (если есть)
            existing_summary: Текущий summary из sessions.summary
            n_ctx:            Размер контекстного окна модели

        Returns:
            ContextResult с готовыми сообщениями и метаданными
        """
        # Бюджет токенов под историю (резервируем под ответ модели)
        budget = int(n_ctx * (1 - RESPONSE_RESERVE))

        # Вычитаем system prompt и summary из бюджета
        system_tokens = self.count_tokens(system_prompt) if system_prompt else 0
        summary_tokens = self.count_tokens(existing_summary) if existing_summary else 0
        history_budget = budget - system_tokens - summary_tokens

        if history_budget <= 0:
            # System prompt + summary уже заняли весь бюджет
            return self._assemble(
                system_prompt, existing_summary, [], 0,
                len(messages), existing_summary,
            )

        # Нормализуем messages → list[dict]
        normalized = self._normalize(messages)

        # Разбиваем на: recent (влезают) и trimmed (не влезают)
        recent, trimmed = self._split_by_budget(normalized, history_budget)

        # Обновляем summary только если есть что добавить
        new_summary = existing_summary
        if trimmed:
            new_summary = self._append_to_summary(existing_summary, trimmed)

        return self._assemble(
            system_prompt=system_prompt,
            summary=new_summary,
            recent=recent,
            system_tokens=system_tokens,
            trimmed_count=len(trimmed),
            new_summary=new_summary if trimmed else None,
        )

    def _normalize(self, messages: list) -> list[dict]:
        """Приводит Message dataclass или dict к единому формату dict."""
        result = []
        for m in messages:
            if isinstance(m, dict):
                result.append({"role": m["role"], "content": m["content"]})
            else:
                # dataclass: Message(role=..., content=...)
                result.append({"role": m.role, "content": m.content})
        return result

    def _split_by_budget(
        self,
        messages: list[dict],
        budget: int,
    ) -> tuple[list[dict], list[dict]]:
        """
        Делит историю на recent (войдут в контекст) и trimmed (уйдут в summary).

        Алгоритм:
          1. Гарантируем MIN_RECENT_MESSAGES последних сообщений
          2. Добавляем остальные с конца пока влезает бюджет
          3. Всё что не влезло — trimmed

        Сообщения режутся ТОЛЬКО по границам — никогда посередине.
        """
        if not messages:
            return [], []

        # Шаг 1: гарантированный хвост
        guaranteed = messages[-MIN_RECENT_MESSAGES:]
        rest = messages[:-MIN_RECENT_MESSAGES]

        # Считаем токены гарантированного хвоста
        used = sum(self.count_tokens(m["content"]) for m in guaranteed)

        # Если даже гарантированный хвост не влезает — берём только его
        if used >= budget:
            trimmed_count = len(rest)
            return guaranteed, rest

        # Шаг 2: добавляем остальные с конца пока влезает
        additional = []
        for msg in reversed(rest):
            tokens = self.count_tokens(msg["content"])
            if used + tokens > budget:
                break           # не влезает целиком — СТОП, не обрезаем
            additional.insert(0, msg)
            used += tokens

        recent = additional + guaranteed
        trimmed = rest[:len(rest) - len(additional)]

        return recent, trimmed

    def _append_to_summary(
        self,
        existing_summary: str,
        trimmed: list[dict],
    ) -> str:
        """
        Добавляет вытолканные сообщения в summary в виде пар Q→A.

        Формат пары: "Q: <первые N символов> → A: <первые N символов>"
        Пары объединяются через " | ".

        Только пары user+assistant — одиночные сообщения пропускаем
        чтобы не было каши из обрывков.
        """
        pairs = []
        i = 0
        while i < len(trimmed):
            msg = trimmed[i]

            if msg["role"] == "user":
                # Ищем следующий assistant
                next_msg = trimmed[i + 1] if i + 1 < len(trimmed) else None
                if next_msg and next_msg["role"] == "assistant":
                    q = msg["content"][:SUMMARY_PAIR_LENGTH // 2].strip()
                    a = next_msg["content"][:SUMMARY_PAIR_LENGTH // 2].strip()
                    # Убираем переносы строк для читаемости
                    q = q.replace("\n", " ")
                    a = a.replace("\n", " ")
                    pairs.append(f"Q: {q} → A: {a}")
                    i += 2
                    continue

            i += 1

        if not pairs:
            return existing_summary

        new_part = " | ".join(pairs)
        if existing_summary:
            return f"{existing_summary} | {new_part}"
        return new_part

    def _assemble(
        self,
        system_prompt: str,
        summary: str,
        recent: list[dict],
        system_tokens: int,
        trimmed_count: int,
        new_summary: Optional[str],
    ) -> ContextResult:
        """Собирает финальный список сообщений для LLM."""
        result = []

        # 1. System prompt — всегда первым
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})

        # 2. Summary старой истории — как system сообщение
        if summary:
            result.append({
                "role": "system",
                "content": f"[Предыдущий контекст разговора]: {summary}",
            })

        # 3. Последние сообщения — целиком
        result.extend(recent)

        total_tokens = sum(self.count_tokens(m["content"]) for m in result)

        return ContextResult(
            messages=result,
            total_tokens=total_tokens,
            was_compressed=trimmed_count > 0,
            trimmed_count=trimmed_count,
            new_summary=new_summary,
        )


# Глобальный singleton
context_manager = ContextManager()
