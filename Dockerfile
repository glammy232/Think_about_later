# Multi-stage build
FROM python:3.12-slim AS builder

WORKDIR /opt/project
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim AS runner

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/project

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:%PATH

COPY app ./app
COPY ai ./ai
COPY frontend ./frontend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
