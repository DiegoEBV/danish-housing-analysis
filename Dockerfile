# syntax=docker/dockerfile:1.6
FROM python:3.14-slim

WORKDIR /app

# Dependencias de sistema minimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# uv: pin a version + digest para builds reproducibles (no `:latest`).
# 0.9.26 es la version usada para generar uv.lock en este repo.
# Renovar via Dependabot/Renovate o `docker manifest inspect ghcr.io/astral-sh/uv:<ver>`.
COPY --from=ghcr.io/astral-sh/uv:0.9.26@sha256:08a7428e3daeb4ff634fe06d3d9aec278579e88f770b5d141e5a408cb998f40a \
     /uv /uvx /bin/

# Metadata primero para aprovechar layer caching
COPY pyproject.toml uv.lock ./

# Sincroniza solo dependencias runtime (sin --extra dev/notebook)
# --frozen exige que uv.lock este al dia; falla rapido si hay drift
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
RUN uv sync --frozen --no-dev --no-editable

# Codigo del pipeline (data/ NO se copia: viene de GCS en runtime)
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY configs/ ./configs/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Entrypoint por defecto: pipeline end-to-end leyendo config local.
# Override del raw / paths via env vars o configs/analysis.yaml montado.
CMD ["python", "scripts/run_pipeline.py", "--config", "configs/analysis.yaml"]
