#!/bin/bash
# LLM Studio — запуск на Apple Silicon (Metal)

set -e

echo "🚀 LLM Studio starting..."
cd "$(dirname "$0")/backend"

# Установка зависимостей если нужно
if ! python -c "import llama_cpp" 2>/dev/null; then
  echo "📦 Installing dependencies with Metal support..."
  CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
  pip install fastapi uvicorn pydantic
fi

echo "✅ Backend: http://localhost:8000"
echo "🌐 Open in browser: http://localhost:8000"
echo ""

python main.py
