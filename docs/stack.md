# Stack

Versiones tomadas de `pyproject.toml`, `package.json` y `Dockerfile` (son mínimos, no lo instalado).

## Backend
- Python 3.12 (`.python-version`), gestor de paquetes **uv**
- FastAPI `>=0.141.1`, Uvicorn `>=0.52.4`
- SQLAlchemy `>=2.0.52`, driver `psycopg[binary] >=3.3.5`
- **Alembic** `>=1.20.1` (migraciones)
- ReportLab `>=5.0.1` (PDF)
- `google-genai >=2.33.0` (Gemini), `httpx >=0.28.1`
- `python-dotenv >=1.2.3`
- **argon2-cffi** `>=25.1.0` (hash de contraseñas, Argon2id)
- Dev: **pytest** `>=9.2.0`, Ruff `>=0.16.6`

## Frontend
- React `^19.2.8`, Vite `^8.2.2`, `@vitejs/plugin-react ^6.1.0`
- pnpm, oxlint `^1.79.0`; Node 22 (el del `Dockerfile`)
- Sin router ni librería de UI: CSS propio (`index.css`, prefijo `nh-`)

## Base de datos
- **Producción:** PostgreSQL en Neon (la cadena va en `DATABASE_URL`).
- **Local:** SQLite (`presupuestos.db`) si `DATABASE_URL` está vacía.
- Dinero: `Numeric(14, 2)`. El esquema lo manejan las migraciones de Alembic.

## Infraestructura
- Docker multi-stage: Node 22 compila el front, Python 3.12 slim corre FastAPI y sirve `frontend/dist`.
  uvicorn arranca con `--proxy-headers --forwarded-allow-ips='*'` (ver `docs/architecture.md`).
- Hosting: Render. [A CONFIRMAR CON EL EQUIPO] si el frontend va separado (Netlify/Vercel) o sirve FastAPI.
- Despliega y mantiene: el autor.
- El `Dockerfile` instala con `uv sync --frozen`: **si se cambia `pyproject.toml`, hay que regenerar `uv.lock`**
  (`uv lock`) y commitearlo, o el build falla.

## Variables de entorno (solo nombres; los valores nunca van al repo)
| Variable | Uso |
|---|---|
| `DATABASE_URL` | Conexión a Postgres. Vacía → SQLite local. |
| `DUENO_USUARIO`, `DUENO_PASSWORD`, `DUENO_NOMBRE` | Primer dueño. Se usa **solo si no hay ningún usuario**; después conviene borrarlas. La contraseña es secreta: va solo como variable de entorno del hosting. |
| `SECRET_KEY` | Firma de la cookie de sesión. **Obligatoria en producción**, aleatoria, ≥ 32 caracteres. |
| `ENV` | `production` o `development`. En `production` se activan las validaciones de arranque. |
| `PORT` | Puerto donde escucha el servidor dentro del contenedor (por defecto 8000). |
| `FRONTEND_ORIGIN` | Origen permitido por CORS en desarrollo. |
| `GEMINI_API_KEY` | Clave del asistente. Vacía → el asistente no aparece. |
| `GEMINI_MODELS` | Modelos en orden de preferencia, separados por coma (opcional). |
| `AGENTE_WEBHOOK_URL` | URL del trigger de Power Automate que ejecuta el agente de Copilot Studio para el chat del ayudante. **Es un secreto** (lleva una clave firmada): solo como variable de entorno. Si está, el chat usa el webhook en lugar de Gemini. |
| `NEGOCIO_NOMBRE`, `NEGOCIO_RUBRO` | Nombre y rubro impresos en el PDF (por defecto "Obras Demo" y su rubro). |
| `NEGOCIO_RESPONSABLE`, `NEGOCIO_TELEFONO`, `NEGOCIO_INSTAGRAM` | Contacto impreso en el PDF. Si están vacías, no se imprimen. |

Plantilla en `backend/.env.example`.

## Deploy en Dokploy (Docker)
El `Dockerfile` de la raíz compila el frontend y lo sirve junto con el backend en un solo contenedor.

**La imagen se construye en GitHub, no en Dokploy.** Los contenedores de build del servidor de Dokploy no resuelven DNS
(`Temporary failure in name resolution` contra PyPI y npm), aunque los contenedores en marcha sí. Arreglarlo requiere
cambiar el DNS de Docker en el servidor, y no hay acceso. Por eso `.github/workflows/imagen.yml`:
- en cada PR construye la imagen (amd64) sin publicarla, como verificación del `Dockerfile`;
- en cada push a `main` la construye para amd64 y arm64, la publica en `ghcr.io/gaelschenone/andamio-demo` (`latest` y
  `sha-<commit>`) y llama al webhook de deploy de Dokploy (secreto del repo `DOKPLOY_DEPLOY_WEBHOOK`).

**Registro en Dokploy** (una sola vez) → Settings → Registry: `ghcr.io`, usuario de GitHub y un token **classic** con solo
`read:packages` (lo crea y lo carga el dueño de la cuenta; no va en el repo).

**Aplicación** → Provider: **Docker** · Image: `ghcr.io/gaelschenone/andamio-demo:latest` · Registry: el de GHCR. Para volver a
una versión anterior, cambiá `latest` por el tag `sha-<commit>` y redeployá.

**Dominio** → Container Port: **8000**, con HTTPS (Let's Encrypt). **No publiques el puerto** del contenedor: el servidor confía en
las cabeceras `X-Forwarded-*` del proxy (Traefik), y eso solo es seguro si todo el tráfico pasa por él.

**Base de datos** → creá un servicio **PostgreSQL** en Dokploy (o usá Neon) y programá sus backups. `DATABASE_URL` acepta la URL
tal como la entrega el servicio (`postgresql://usuario:clave@host:5432/base`): la app le agrega el driver `psycopg`. Sin
`DATABASE_URL` la app usa SQLite **dentro del contenedor**: los datos se pierden en cada redeploy (en producción lo avisa en el log).

**Variables de entorno** (Environment de la aplicación):

| Variable | Valor |
|---|---|
| `ENV` | `production` (activa la cookie `Secure` y las validaciones de arranque) |
| `SECRET_KEY` | `openssl rand -hex 32` |
| `DATABASE_URL` | la del servicio PostgreSQL |
| `DUENO_USUARIO`, `DUENO_PASSWORD`, `DUENO_NOMBRE` | solo para el primer arranque; después borrá `DUENO_PASSWORD` |
| `GEMINI_API_KEY` o `AGENTE_WEBHOOK_URL` | opcionales: sin ninguna, el asistente no aparece. Son secretos |
| `NEGOCIO_*` | datos de contacto del PDF |

**Detalles que importan**
- **Un solo contenedor y un solo proceso:** el límite de intentos de login y los candados de agenda y cobros viven en memoria. No subas réplicas ni workers.
- **Healthcheck:** la imagen trae uno propio contra `/api/health`; en Dokploy podés usar la misma ruta.
- **Migraciones:** las aplica la app al arrancar.
- **Usuario sin privilegios:** el proceso corre como `app` (uid 10001), no como root.
- Para probar la imagen en otra máquina: `docker build -t andamio .` y `docker run --rm -p 8000:8000 -e ENV=production -e SECRET_KEY=... -e DUENO_USUARIO=... -e DUENO_PASSWORD=... andamio`.

