FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir uv \
    && uv pip install --system \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.32.0" \
        "websockets>=14.0" \
        "httpx>=0.28.0" \
        "python-dotenv>=1.0.0"

COPY . .

EXPOSE 5050
CMD ["python", "start.py"]
