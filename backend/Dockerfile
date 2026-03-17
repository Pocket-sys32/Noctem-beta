FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir uv \
    && uv pip install --system \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.32.0" \
        "httpx>=0.28.0" \
        "python-dotenv>=1.0.0" \
        "supabase>=2.11.0" \
        "pydantic>=2.10.0" \
        "openai>=1.60.0"

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
