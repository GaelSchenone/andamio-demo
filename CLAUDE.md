# Andamio Demo — gestión de obras (versión de demostración)

Demo **pública** de Andamio, un sistema de gestión para una empresa de pintura y reparaciones: clientes y obras,
presupuestos con PDF, calendario de trabajos y cobros. Todo lo que se ve es **ficticio** y la marca ("Obras Demo")
es inventada. Se arma a partir del repo real (privado) con un historial nuevo, para la entrega del curso.

## Qué es de mentira
- **Datos:** con `DEMO=1`, si la base está vacía, la app arranca y se siembra sola (`demo.py`): usuarios `demo`
  (dueño) y `empleada`, clientes, presupuestos, trabajos y cobros inventados, con fechas relativas a hoy.
- **Asistente de IA:** con `AGENTE_SIMULADO=1` el chat y "Completar con IA" contestan por reglas (`simulado.py`),
  sin Gemini ni webhooks ni claves. Usa las mismas herramientas y permisos que el asistente real.
- **Base:** sin `DATABASE_URL` es SQLite dentro del contenedor: cada deploy vuelve a sembrar los datos.

## Stack
React 19 + Vite (frontend) · FastAPI + SQLAlchemy (backend, Python 3.12) · PostgreSQL (SQLite en el demo)
· Gemini vía `google-genai` (en el demo, simulado) · Docker · GitHub Actions + Dokploy. Detalle en `docs/stack.md`.

## Reglas que no se negocian
- **Cero credenciales en el código o el historial.** Todo por variables de entorno; `.env` y `*.db`
  están en `.gitignore`. Si aparece una clave en un commit: revocarla, no solo borrarla.
- **Datos personales de clientes** (Ley 25.326): no se loguean valores, no se suben datos reales a
  ningún repo. Los pedidos que van a Gemini pueden traer datos de clientes → ver `docs/architecture.md`.
- **No se agenda un trabajo sin presupuesto aprobado**, y la agenda es única (sin superposiciones).
- **Permisos:** cada endpoint exige un permiso (`requiere_permiso("...")`), nunca un rol. La matriz vive solo
  en `permisos.py`. El empleado **no ve precios, presupuestos ni cobros**; hay tests que lo exigen.
- **Ningún endpoint que vea el empleado devuelve precios.** Los trabajos se arman campo por campo (`routers/trabajos.py`).
- **Un presupuesto aprobado no se edita ni se borra**, y solo se aprueba con cliente y obra. Un presupuesto tiene a lo
  sumo un trabajo vigente (índice único parcial en la base).
- **Contraseñas** solo como hash Argon2 (`passwords.py`); nunca se loguean ni se devuelven por la API.
- **Dinero:** columnas `Numeric` y cuentas con `Decimal`, nunca `float`.
- **Cambios de modelos = migración de Alembic** (`uv run alembic revision --autogenerate -m "..."`); un test lo exige.
- **Datos de contacto del negocio** solo por variables `NEGOCIO_*`, nunca escritos en el código (un test lo exige).
- Si cambia `pyproject.toml`, regenerar `uv.lock` (el `Dockerfile` instala con `--frozen`).

## Comandos
- Backend: `cd backend && uv sync && uv run uvicorn presupuestos_backend.main:app --reload`
- Tests: `cd backend && uv run pytest` (309 tests; usan una base SQLite temporal, nunca datos reales)
- Usuarios por terminal: `cd backend && uv run python -m presupuestos_backend.usuarios_cli --help`
  (crear usuarios o recuperar la contraseña del dueño). El primer dueño sale de `DUENO_USUARIO` y `DUENO_PASSWORD`.
- Migraciones a mano: `cd backend && uv run alembic upgrade head` (la app también las aplica al arrancar)
- Frontend: `cd frontend && pnpm install && pnpm dev` (proxy de `/api` a `127.0.0.1:8000`) · tests: `pnpm test` (Vitest) · galería de componentes en `/kit.html` (solo en desarrollo)
- Commits: Conventional Commits, validados por un hook. Activarlo una vez por clon: `git config core.hooksPath .githooks`.
- Lint: `cd backend && uv run ruff check . && uv run ruff format --check .` · `cd frontend && pnpm lint`
- Docker: el `Dockerfile` compila el front y lo sirve desde FastAPI en un solo servicio. La imagen la construye
  GitHub Actions (`.github/workflows/imagen.yml`) y Dokploy la descarga de GHCR: el build en el servidor no tiene DNS.

Verificado: `uv sync`, `pytest`, `ruff`, arranque de uvicorn, `pnpm install`, `pnpm lint` y `pnpm build`.
El build de la imagen del `Dockerfile` (amd64) se verifica en GitHub Actions en cada PR.
**No verificado:** `pnpm dev` y el arranque del contenedor (no hay Docker en esta máquina; sí se reprodujeron sus pasos a mano en una copia limpia y se probó el arranque).

## Documentación
- [`docs/architecture.md`](docs/architecture.md) — arquitectura, modelo de dominio, reglas, deuda técnica
- [`docs/stack.md`](docs/stack.md) — tecnologías y variables de entorno
- [`docs/workflows.md`](docs/workflows.md) — flujos de negocio
- [`docs/conventions.md`](docs/conventions.md) — convenciones de código y commits
- [`docs/decisiones.md`](docs/decisiones.md) — reglas de negocio aplicadas, quién las decidió y qué falta validar con el dueño
- [`docs/roadmap.md`](docs/roadmap.md) — MVP, después del MVP y repo demo

## Interfaz
Dashboard con navegación lateral (≥1024 px), riel (720–1023) y barra inferior (celular); rutas con `react-router-dom`.
Kit de componentes en `frontend/src/ui/`, pantallas en `frontend/src/pages/`, estructura en `frontend/src/layout/`.
Colores solo en `styles/tokens.css`; CSS junto a cada componente. Decisiones en `docs/decisiones.md` (D-27 a D-29).
El backend sirve `index.html` ante rutas del navegador (`spa.py`), para que recargar en `/clientes/3` funcione.

## Ayudante con IA
Chat con Gemini (la orbe abajo a la derecha) que explica cómo usar la app y busca datos. **Solo lectura**, con los permisos
de quien habla y datos mínimos hacia Gemini (sin teléfonos ni notas). Código: `backend/src/presupuestos_backend/agente.py`
(herramientas), `agente_guia.py` (lo que sabe de la app: actualizar si cambia una pantalla) y `frontend/src/layout/agente/`.
Si cambia lo que puede ver un rol, se revisa `construir_herramientas`. Decisión D-31. Motor: Gemini (`GEMINI_API_KEY`) o,
si está `AGENTE_WEBHOOK_URL`, el agente de Copilot Studio por webhook (`webhook.py`; la URL es un secreto, solo en el entorno).

## Pendientes abiertos
Ver secciones `[PENDIENTE]` y `[A CONFIRMAR]` en `docs/`. Lo más importante: reglas de reprogramación
y qué hacer con los PDFs de presupuestos anteriores (D-26 en `docs/decisiones.md`).
