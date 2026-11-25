# Andamio en un solo contenedor: compila el frontend (React) y lo sirve junto con el backend (FastAPI).
# La construye GitHub Actions (.github/workflows/imagen.yml) y Dokploy descarga la imagen de GHCR; también
# se puede construir en cualquier host con `docker build .` (contexto en la raíz del repo, puerto 8000).

# --- 1) Frontend --------------------------------------------------------------------------------------
# Se compila en la arquitectura de la máquina que construye ($BUILDPLATFORM): el resultado son archivos
# estáticos que sirven igual en amd64 y arm64, y así no se emula Node al construir para otra arquitectura.
FROM --platform=$BUILDPLATFORM node:22-slim AS frontend-build
WORKDIR /app/frontend
# pnpm con la misma versión con la que se generó pnpm-lock.yaml. Se instala con npm y no con corepack:
# corepack verifica firmas y suele fallar con versiones nuevas de pnpm.
RUN npm install -g pnpm@12.21.0
# Primero solo los archivos de dependencias: esa capa se reutiliza mientras no cambien.
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ .
RUN pnpm run build

# --- 2) Backend + frontend compilado ------------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/backend/.venv/bin:$PATH"
RUN pip install --no-cache-dir uv==0.13.9 \
    && useradd --system --uid 10001 --home-dir /app app
WORKDIR /app/backend
# Dependencias primero (capa estable) y después el código: tocar el código no reinstala todo.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project
COPY backend/ .
RUN uv sync --no-dev --frozen
# La app busca el frontend en ../frontend/dist, relativo a donde está el código (ver main.py).
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
# El usuario sin privilegios necesita escribir en esta carpeta solo si no hay DATABASE_URL (SQLite local).
RUN chown app:app /app/backend
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8000'), timeout=4)"

# Un solo proceso, a propósito: el límite de intentos de login y los candados de agenda y cobros viven en
# memoria (ver docs/architecture.md, deuda técnica). Con varios workers o réplicas dejarían de ser confiables.
# --proxy-headers: detrás del proxy (Traefik en Dokploy) la IP real del visitante viene en X-Forwarded-For,
# y el límite de intentos la necesita. Confiar en '*' es seguro solo si el servicio recibe tráfico únicamente
# a través del proxy: en Dokploy, no publiques el puerto del contenedor; usá solo el dominio.
# `exec` hace que uvicorn sea el proceso principal y reciba la señal de apagado.
CMD ["sh", "-c", "exec uvicorn presupuestos_backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
