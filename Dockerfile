# ============================================================
# Stage 1 — Builder: install dependencies with uv
# ============================================================
FROM python:3.11-slim AS builder

# Install uv (build-time tool; won't be in the final image)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency manifests + README (referenced by pyproject.toml metadata)
COPY pyproject.toml uv.lock README.md ./

# Install deps into /app/.venv (isolated inside the builder stage)
RUN uv sync --frozen --no-dev

# ============================================================
# Stage 2 — Runtime: minimal image, only what's needed to run
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Copy the built virtualenv from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code and data
COPY src/ ./src/
COPY data/ ./data/

# Put the venv on PATH so `uvicorn` resolves without `uv run`
ENV PATH="/app/.venv/bin:$PATH"

# # Security: run as a non-root user
# RUN adduser --system --uid 1000 appuser
# USER appuser

EXPOSE 8000

# No more `uv run` needed — uvicorn is directly on PATH
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
