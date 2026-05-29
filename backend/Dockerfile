FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1001 appuser

COPY --from=builder /root/.local /home/appuser/.local

COPY --chown=appuser:appuser app/__init__.py ./app/__init__.py
COPY --chown=appuser:appuser app/main.py ./app/main.py
COPY --chown=appuser:appuser app/api/ ./app/api/
COPY --chown=appuser:appuser app/core/ ./app/core/
COPY --chown=appuser:appuser app/db/ ./app/db/
COPY --chown=appuser:appuser app/models/ ./app/models/
COPY --chown=appuser:appuser app/services/ ./app/services/
COPY --chown=appuser:appuser start.sh .

RUN mkdir -p uploads faiss_index logs \
    && chown -R appuser:appuser uploads faiss_index logs \
    && chmod +x start.sh

ENV PATH="/home/appuser/.local/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

CMD ["./start.sh"]
