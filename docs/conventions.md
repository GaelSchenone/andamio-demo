# Convenciones

Relevadas del código y del historial existentes; sirven para mantener el estilo.

## Idioma
- Dominio, nombres de módulos, funciones, campos y mensajes al usuario: **español** (`crud.py`, `crear_presupuesto`,
  `cliente_obra`, `routers/presupuestos.py`). Mantenerlo para entidades nuevas (`trabajo`, `cobro`, `obra`).
- Textos de cara al usuario en español rioplatense, con voseo ("Revisá estos datos").
- Docstrings de módulo en español, explicando el porqué.

## Backend (Python)
- Ruff: `line-length = 100`, `target-version = py312`, reglas `E, F, I, UP, B, SIM` (se ignora `B008` por `Depends`).
- Capas: `routers/` (HTTP) → `crud.py` (base de datos) → `models.py`; datos de entrada y salida en `schemas.py`.
  Las reglas de negocio nuevas (agenda, estados) van en un módulo de servicio, no dentro del router.
- Validación con Pydantic (`Field`); los errores 422 se traducen en `validacion.py`.
- Reglas de negocio en `crud*.py`, no en los routers: se lanzan `ReglaDeNegocio` (el router responde 409 con el mismo
  mensaje) o `VinculoInvalido` (422). Las que protegen datos importantes además se refuerzan en la base (índices
  únicos, claves foráneas), por si dos pedidos llegan a la vez.
- **Nunca loguear valores** de campos de clientes; solo nombre del campo y tipo de error. Tampoco lo que se busca:
  las búsquedas van en la URL y `logs.py` la recorta en el log de acceso. Un endpoint nuevo que reciba datos de
  personas por la URL tiene que seguir cubierto por ese filtro.
- Acceso protegido con `dependencies=[Depends(requiere_permiso("..."))]` a nivel de router. Los endpoints piden un
  **permiso**, nunca un rol; qué permisos tiene cada rol se define únicamente en `permisos.py`.
- Todo endpoint nuevo lleva un test de que el empleado recibe 403 si no debería poder usarlo.
- Contraseñas: solo `passwords.hashear` / `verificar`. Nunca en logs, respuestas ni mensajes de error.

## Frontend (React)
- Componentes funcionales en `components/`, archivos `PascalCase.jsx`; utilidades en minúscula (`api.js`, `formato.js`).
- Toda llamada de red pasa por `api.js`; los errores se muestran con mensajes legibles.
- Clases CSS con prefijo `nh-`, variables CSS para colores. Respetar `prefers-reduced-motion` (ya lo hace `magia.js`).
- `limites.js` replica los límites del backend: si cambian en `schemas.py`, cambiarlos ahí también.
- Lint con oxlint.

## Git
- Commits al estilo Conventional Commits en español, en minúscula (un hook en `.githooks/commit-msg` lo exige; se activa una vez por clon con `git config core.hooksPath .githooks`): `feat: ...`, `fix: ...`, `style: ...`
  (así está el historial del repo original).
- Una rama por funcionalidad (`feat/...`). No commitear `.env`, `*.db`, volcados de datos ni PDFs de clientes.

## Seguridad
- Secretos solo por variable de entorno; agregar la variable nueva (sin valor) a `backend/.env.example`.
- Antes de cada push: buscar claves y datos de clientes en el diff.

## Dinero y base de datos
- Importes: `Numeric(14, 2)` en la base y `Decimal` en las cuentas (`crud.a_dinero`). Nunca `float`.
- Todo cambio en `models.py` lleva su migración en `backend/alembic/versions/`; `test_migraciones.py` falla si falta.
  Las migraciones deben funcionar también sobre una base ya existente (ver `0001`, que no pisa tablas).

## Tests
- pytest en `backend/tests/`; correr con `uv run pytest`. Usan una base SQLite temporal y variables de entorno
  fijadas en `conftest.py`, así que no tocan datos reales ni leen un `.env` local.
- Cada bug que se encuentra lleva un test que lo reproduce (ver los de cookie inválida y nombre de PDF con tildes).
- Las reglas de agenda, estados y cobros del MVP (casos borde de `docs/architecture.md`) se testean al implementarlas.
- [PENDIENTE] cobertura mínima: el equipo no definió un estándar.
