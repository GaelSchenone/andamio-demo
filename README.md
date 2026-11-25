# Andamio Demo

Versión de **demostración** de Andamio, un sistema de gestión de obras para una empresa de pintura y reparaciones:
clientes y obras, presupuestos con PDF, calendario de trabajos y cobros.

> Todo es **ficticio**: la marca ("Obras Demo"), los clientes, los precios y los teléfonos son inventados.
> El asistente de IA está **simulado** (contesta por reglas, no usa ningún modelo). No cargues datos reales.

## Probarlo
Con `DEMO=1` la app arranca con datos de ejemplo, con fechas relativas a hoy:

| Usuario | Contraseña | Rol |
|---|---|---|
| `demo` | `demo-obras-2026` | Dueño: ve todo, incluidos precios, presupuestos y cobros |
| `empleada` | `demo-obras-2026` | Empleada: ve la agenda, los trabajos y los clientes, sin plata |

Son credenciales públicas a propósito. Los datos se vuelven a cargar en cada despliegue.

## Qué está simulado
- **Chat del asistente** (la orbe abajo a la derecha): responde por palabras clave, con los datos de la demo y los
  mismos permisos que el asistente real (la empleada no recibe importes). Avisa en pantalla que es una simulación.
- **"Completar con IA"** del presupuesto: separa las tareas de un texto, detecta medidas (`12 m2`) y precios
  (`45 lucas`, `45k`) y arma un borrador. No entiende lenguaje libre.

## Correrlo en local
Requisitos: Python 3.12 con [uv](https://docs.astral.sh/uv/), Node con pnpm.

```bash
cp backend/.env.example backend/.env
# En backend/.env: DEMO=1 y AGENTE_SIMULADO=1

# Backend (http://127.0.0.1:8000). Crea y migra la base solo al arrancar.
cd backend && uv sync && uv run uvicorn presupuestos_backend.main:app --reload

# Frontend (http://localhost:5173), en otra terminal
cd frontend && pnpm install && pnpm dev

# Tests y lint
cd backend && uv run pytest && uv run ruff check .
cd frontend && pnpm test && pnpm lint
```

## Desplegarlo
El `Dockerfile` arma un solo contenedor (FastAPI sirve la API y el frontend compilado). GitHub Actions construye la
imagen en cada push a `main` y la publica en `ghcr.io/gaelschenone/andamio-demo`. Variables y pasos en
[`docs/stack.md`](docs/stack.md); para el demo alcanza con `ENV=production`, `SECRET_KEY`, `DEMO=1` y `AGENTE_SIMULADO=1`.

## Documentación
[`CLAUDE.md`](CLAUDE.md) (resumen y reglas) y [`docs/`](docs/) (arquitectura, flujos, decisiones, stack).
