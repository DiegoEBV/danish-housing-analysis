FROM python:3.12-slim

WORKDIR /app

# Dependencias de sistema minimas (parquet/numpy a veces necesitan libstdc++)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codigo del pipeline (no incluye data/ — viene de GCS en runtime)
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY configs/ ./configs/

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Entrypoint: pipeline end-to-end leyendo config desde /app/configs/analysis.yaml
# Override de raw_parquet/silver/gold via env vars o config montado.
CMD ["python", "scripts/run_pipeline.py", "--config", "configs/analysis.yaml"]
