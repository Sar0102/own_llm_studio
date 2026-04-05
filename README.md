# LLM Studio

Локальная замена LM Studio — FastAPI бэкенд + веб-интерфейс.
Работает напрямую через `llama-cpp-python` с Metal ускорением (Apple Silicon).

## Быстрый старт

```bash
# 1. Установить зависимости
cd backend
CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
pip install -r requirements.txt

# 2. Запустить
python main.py

# 3. Открыть браузер
open http://localhost:8000
```

Или одной командой:
```bash
chmod +x run.sh && ./run.sh
```

## Использование

1. В поле **Models Directory** укажи папку с `.gguf` файлами
2. Нажми **Scan** — найдёт все модели
3. Выбери модель из списка
4. Настрой параметры (temperature, context и т.д.)
5. Нажми **Load Model**
6. Чатись

## API

Бэкенд совместим с OpenAI API формата:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000",
    api_key="local",
    model="any",
)
```

## Структура

```
llm-studio/
├── backend/
│   ├── main.py          # FastAPI роуты
│   ├── llm_manager.py   # Singleton менеджер модели
│   └── requirements.txt
├── frontend/
│   └── index.html       # React UI
└── run.sh
```
