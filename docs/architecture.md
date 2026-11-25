# Arquitectura

## Visión general
Aplicación web de ciclo completo en **un solo servicio** desplegable: FastAPI expone la API bajo
`/api` y, si existe `frontend/dist`, sirve también el frontend compilado (`main.py`). En desarrollo
el frontend corre aparte con Vite y hace proxy de `/api` al backend.

```
Navegador (React) ──/api──▶ FastAPI ──▶ SQLAlchemy ──▶ PostgreSQL (Neon) / SQLite (local)
                              ├──▶ Alembic (migraciones, al arrancar)
                              ├──▶ ReportLab (PDF en memoria)
                              └──▶ Gemini (google-genai)
```

## Backend (`backend/src/presupuestos_backend/`) — implementado hoy
| Módulo | Responsabilidad |
|---|---|
| `main.py` | Arma la app, CORS, handler de validación, sirve el frontend. Al arrancar valida la configuración y aplica migraciones. |
| `database.py` | Engine y sesión; elige SQLite o Postgres según `DATABASE_URL`. |
| `migraciones.py` + `backend/alembic/` | Migraciones de esquema (Alembic). Se aplican solas al arrancar. |
| `models.py` | `Presupuesto` e `ItemPresupuesto`. Dinero en `Numeric(14, 2)`. |
| `schemas.py` | Esquemas Pydantic de entrada/salida y del borrador de IA. Topes: importe ≤ 999.999.999, ≤ 200 ítems. |
| `crud.py` | Operaciones de base de datos; la plata se calcula con `Decimal` (redondeo "a mano", 10,005 → 10,01). |
| `routers/presupuestos.py` | CRUD + `GET /{id}/pdf` (nombre de archivo con tildes en UTF-8, RFC 6266). |
| `routers/auth.py`, `auth.py`, `ratelimit.py` | Login con usuario y contraseña, cookie firmada (HMAC) con versión de sesión, límite de intentos fallidos, cambio de la propia contraseña. |
| `routers/usuarios.py`, `crud_usuarios.py`, `schemas_usuarios.py` | Gestión de usuarios (solo dueño): alta, rol, desactivar, restablecer contraseña. |
| `routers/cobros.py`, `crud_cobros.py`, `schemas_cobros.py` | Cobros (seña y saldo) y lista de lo que falta cobrar. Solo dueño. Toda la plata con `Decimal`. `crud_cobros.recalcular_estado` decide cuándo un trabajo pasa a "cobrado". |
| `routers/trabajos.py`, `crud_trabajos.py`, `schemas_trabajos.py` | Trabajos y su calendario. Ver, iniciar y terminar: dueño y empleado, **sin ningún precio** (el esquema no los incluye). Crear, agendar, reprogramar, cancelar y ver el historial de cambios de fecha: solo dueño. La regla de agenda única vive en `crud_trabajos._verificar_agenda_libre`. |
| `errores.py` | `ReglaDeNegocio` (→ HTTP 409) y `VinculoInvalido` (→ 422): los endpoints las traducen con el mismo mensaje. |
| `routers/clientes.py`, `crud_clientes.py`, `schemas_clientes.py` | Clientes (casa | consorcio) y sus obras (direcciones). Leer: dueño y empleado. Escribir: solo dueño. Búsqueda por nombre, teléfono o dirección. |
| `logs.py` | Filtro del log de acceso: saca el `?buscar=...` de la URL para que no queden datos de clientes en los logs. |
| `permisos.py` | Matriz de permisos por rol: única fuente de verdad. Los endpoints piden permisos, no roles. |
| `passwords.py` | Hash Argon2id; verificación contra un hash falso cuando el usuario no existe (mismo tiempo de respuesta). |
| `bootstrap.py`, `usuarios_cli.py` | Primer dueño desde variables de entorno; gestión de usuarios y recuperación desde la terminal. |
| `routers/asistente.py`, `llm.py` | Asistente IA: texto libre → borrador de presupuesto. |
| `pdf_generator.py`, `negocio.py` | PDF en memoria (`BytesIO`); los datos de contacto salen de variables de entorno. |
| `validacion.py` | Convierte errores 422 en mensajes en castellano; no loguea valores. |

Endpoints: `/api/health`, `/api/auth/{estado,login,logout}`, `/api/presupuestos` (CRUD y `/{id}/pdf`),
`/api/asistente/{estado,presupuesto}`, `/api/usuarios`, `/api/clientes` (y `/{id}/obras`), `/api/obras/{id}`, `/api/trabajos`
(y `/{id}/agendar`, `/reprogramar`, `/reprogramaciones`, `/iniciar`, `/terminar`, `/cancelar`), `/api/presupuestos/{id}/estado` y `/api/presupuestos/{id}/trabajo`.

## Frontend (`frontend/src/`) — implementado hoy
SPA sin router: `App.jsx` alterna entre pestañas "nuevo" e "historial". Capa de red en `api.js`.
Componentes en `components/` (`NuevoPresupuesto`, `Historial`, `AsistenteIA`, `Login`, …).
`limites.js` duplica a mano los límites de largo del backend.

## Base de datos y migraciones
- Toda modificación de `models.py` necesita una migración en `backend/alembic/versions/`
  (`uv run alembic revision --autogenerate -m "..."`). Un test (`test_las_migraciones_coinciden_con_los_modelos`)
  falla si falta.
- `0001` es la base y es *idempotente*: si la base ya la creó la versión anterior de la app (con `create_all`),
  no pisa las tablas. `0002` pasa los importes de `Float` a `Numeric(14, 2)`.
- Las migraciones corren al arrancar la app. Es seguro con **un solo worker** (como está hoy el `Dockerfile`);
  con varios workers habría que correrlas como paso aparte.

## Modelo de dominio objetivo (MVP) — PROPUESTO, no implementado
- **Usuario** (rol: dueño | empleado) — **implementado**
- **Cliente** (nombre, tipo: casa | consorcio, teléfono, notas) — **implementado**
- **Obra** (cliente, dirección, referencia, notas) — **implementado**. Un cliente tiene varias; la `referencia`
  distingue las del mismo cliente ("Depto 3B", "Hall y escaleras").
- **Presupuesto** + estado (borrador | enviado | aprobado | rechazado) + cliente y obra opcionales — **implementado**.
  El texto libre `cliente_obra` y `direccion` se conserva como "foto" del momento: si después cambian los datos del
  cliente, los PDF ya emitidos no se alteran. Los presupuestos viejos quedaron como borrador y sin vínculo.
- **Trabajo** (presupuesto aprobado, estado, fecha de inicio y de fin) — **implementado**. Estados: por agendar →
  agendado → en curso → terminado → cobrado (y cancelado). "Cobrado" significa terminado y pagado por completo.
  No guarda precios ni datos del cliente: se leen del presupuesto, la obra y el cliente.
  La base exige que las dos fechas vayan juntas (o ninguna) y que el fin no sea anterior al inicio.
- **Reprogramación** (trabajo, fechas anteriores y nuevas, causa, motivo, usuario, cuándo) — **implementada**:
  cada cambio de fecha queda registrado y no se puede borrar.
- **Cobro** (trabajo, concepto: seña | saldo, monto, fecha del pago, nota, quién lo registró, anulación) —
  **implementado**. El monto es dinero exacto (`Numeric`, nunca `float`) y la base exige que sea mayor a cero. No se
  edita ni se borra: se anula, y queda quién lo anuló y cuándo.

## Reglas de negocio objetivo
1. Un trabajo solo se crea a partir de un presupuesto **aprobado** — **implementado**. Reglas asociadas, también
   implementadas (propuestas por mí y aprobadas por el autor de forma provisoria; falta validarlas con el dueño,
   ver `docs/decisiones.md`):
   - Para **aprobar** un presupuesto hace falta cliente **y** obra (todo trabajo tiene que tener adónde ir).
   - Un presupuesto **aprobado no se edita ni se borra**: protege lo acordado. Hay que pasarlo a otro estado primero.
   - A un presupuesto con **trabajo vigente** no se le puede sacar la aprobación: primero se cancela el trabajo.
   - Hay a lo sumo **un trabajo vigente** por presupuesto. Lo garantiza la base con un índice único parcial
     (`uq_trabajo_vigente_por_presupuesto`), así que un doble clic o dos pedidos simultáneos no lo duplican.
   - Un trabajo se cancela mientras no empezó ("por agendar" o "agendado"; esto último amplía lo que el autor aprobó y
     está por confirmar, ver D-15). Un presupuesto con trabajos, aun cancelados, no se borra.
   - No se borra un cliente ni una obra que tengan presupuestos asociados.
2. **Agenda única — implementada:** dos trabajos no pueden compartir ningún día (los extremos cuentan; días seguidos
   sin compartir ninguno sí se permiten). Los cancelados y los sin fechas no ocupan lugar; uno terminado sigue
   ocupando sus días. [A CONFIRMAR CON EL DUEÑO] si alguna vez hace dos trabajos chicos el mismo día (Q-01, D-13).
3. **Días corridos — implementado como supuesto:** un trabajo dura de su fecha de inicio a la de fin, ambas
   inclusive, hasta 366 días. No hay regla de sábados, domingos ni feriados; el calendario los marca pero no los
   bloquea. [A CONFIRMAR CON EL DUEÑO] (Q-02, D-14).
4. **Reprogramar — implementado:** solo un trabajo agendado o en curso, por cualquier motivo: se elige una causa
   (clima, cliente, materiales u otra) y el detalle escrito es opcional; conserva el historial con quién lo hizo y cuándo. Un trabajo en curso solo cambia su
   fecha de fin. No hay reglas automáticas por clima. [A CONFIRMAR CON EL DUEÑO] (Q-03, D-16).
5. **Cobros — implementados** (ver `docs/decisiones.md`, D-18 a D-24). Lo que se cobra es el total del presupuesto,
   siempre en dos partes: 50% de seña y el resto de saldo. El sistema **sugiere** esos montos pero acepta otros.
   - La suma de cobros vigentes **nunca supera el total**; el mensaje dice cuánto falta, en formato argentino.
   - Un trabajo pasa a **"cobrado"** cuando está terminado y pagado por completo. Si ya estaba todo pagado al
     terminarlo, pasa directo. Si se anula un cobro de un trabajo cobrado, vuelve a "terminado".
   - Un cobro **no se edita ni se borra**: se anula y deja de contar, con registro de quién y cuándo.
   - **No se cancela un trabajo con cobros vigentes**: primero se anulan (por ejemplo, al devolver la seña).
   - La seña **no bloquea** iniciar el trabajo: solo se ve qué falta cobrar.
   - Solo el dueño ve y maneja los cobros. El empleado nunca ve plata, ni siquiera en los trabajos.
6. Roles: ver la matriz en `permisos.py` (resumen en "Seguridad"). Falta aplicar los permisos de agenda, trabajos,
   clientes y cobros cuando existan esos endpoints; cada uno debe llevar su test de 403 para el empleado.

## Seguridad y datos personales
- **Ley 25.326:** el sistema guarda nombres, direcciones y teléfonos de clientes. Antes de usarlo con datos
  reales hay que confirmar con el área correspondiente quién es responsable de la base y el tratamiento.
  [A CONFIRMAR CON EL ÁREA CORRESPONDIENTE]
- **El empleado nunca ve precios**, ni siquiera por una pantalla de trabajos: la respuesta de `/api/trabajos` se arma
  campo por campo y su esquema no tiene importes, total ni forma de pago. Un test busca esas palabras y un importe
  concreto en lo que recibe el empleado.
- **Datos de clientes guardados:** solo nombre, tipo, teléfono, notas y las direcciones de sus obras (minimización).
  El empleado los ve (decisión del autor, a validar con el dueño: ver `docs/decisiones.md`). Se pueden borrar —derecho de supresión— pero solo si el cliente ya no
  tiene obras: la regla evita dejar trabajos sin cliente; hay que borrar primero las obras.
- **Logs:** nada de lo que escribe una persona debe quedar en los logs. El log de acceso de uvicorn guardaba la URL
  completa, y las búsquedas viajan en la URL (`?buscar=nombre`); `logs.py` lo filtra y un test lo exige. Los errores 422
  registran el campo, nunca el valor.
- **Gemini:** el asistente envía a Google el texto del pedido, que puede incluir datos de clientes. En el plan
  gratuito Google puede usar esos textos para entrenar sus modelos (advertencia ya presente en `.env.example`).
  Recomendación: clave paga. También es una transferencia internacional de datos: [A CONFIRMAR CON EL ÁREA CORRESPONDIENTE].
- **Auth:** usuarios con rol (dueño | empleado). Cookie `httponly`, `secure` en producción, de 30 días.
  - La cookie lleva `id.version.vencimiento.firma`. En **cada pedido** se busca al usuario en la base: si está
    desactivado o su `version_sesion` cambió (cambio o restablecimiento de contraseña, desactivación), la cookie
    deja de valer aunque la firma sea correcta. El rol también se lee siempre de la base, así que bajarle el rol a
    alguien le quita permisos al instante.
  - Las contraseñas se guardan solo como hash Argon2id (10 a 128 caracteres). "No existe", "está desactivado" y
    "contraseña incorrecta" dan el mismo mensaje.
  - No hay registro abierto. El primer dueño sale de `DUENO_USUARIO` / `DUENO_PASSWORD` al arrancar, solo si no hay
    usuarios. Siempre queda al menos un dueño activo.
  - En producción (`ENV=production`) la app **no arranca** con una `SECRET_KEY` por defecto o de menos de 32 caracteres.
  - **Permisos del empleado** (decididos por el autor, a validar con el dueño del negocio: `docs/decisiones.md`): ve la agenda, cambia el estado de un trabajo y ve
    clientes y direcciones. **No** ve precios, presupuestos ni cobros, y no gestiona usuarios.
  - Tras 5 intentos fallidos desde una IP, el login se bloquea 15 minutos (429). Cambiar la contraseña tiene su propio
    límite por usuario (por si roban una sesión).
    El límite es en memoria y de un solo proceso. Detrás de Render la IP real viene en `X-Forwarded-For`; por eso el
    `Dockerfile` arranca uvicorn con `--proxy-headers --forwarded-allow-ips='*'` (válido porque el servicio solo recibe
    tráfico a través de ese proxy). [A CONFIRMAR] que el hosting elegido se comporte igual.
- **Datos del negocio en el PDF** (nombre de contacto, teléfono, Instagram): variables `NEGOCIO_*`, nunca en el código.
  Un test falla si vuelven a aparecer escritos a mano.
- Los PDF se generan en memoria; no se guarda nada en disco (el disco de Render es efímero).

## Entornos y datos
- **Real** (este repo): instancia del negocio real, que es otro repositorio privado.
- **Demo** (`andamio-demo`): datos ficticios, repo público, para la entrega del curso.
- **Presupuestos anteriores:** lo que existe hoy son solo PDFs, no una base de datos, así que no hay nada que migrar
  con un script. Se conservan como archivo y, si algún trabajo sigue vigente, se vuelve a cargar a mano cuando el autor
  apruebe la app final (D-26). Esos PDFs contienen datos de clientes (Ley 25.326): **nunca se commitean**; el
  `.gitignore` bloquea todos los `.pdf` salvo la plantilla del negocio.

## Deuda técnica
**Resuelta en la Fase 0:** importes en `Numeric` con aritmética `Decimal`; migraciones con Alembic; datos de contacto
fuera del código; `datetime.utcnow` reemplazado; clave comparada en tiempo constante; límite de intentos de login;
arranque seguro en producción; `httpx` como dependencia directa; primeros tests; y dos bugs que aparecieron al
testear (cookie con caracteres no ASCII o sin número daba error 500; nombre del PDF con tildes o caracteres fuera
de latin-1 rompía el header).

**Pendiente:**
- No hay recuperación de contraseña por mail: la hace el dueño desde la app, o el autor con `usuarios_cli`.
- El límite de intentos es por IP y en memoria (un solo proceso). No hay bloqueo por usuario, a propósito: dejaría
  a un atacante bloquear al dueño.
- **La agenda única no está garantizada por la base de datos.** La regla se revisa en el código, dentro de un candado
  del proceso: alcanza mientras la app corra en un solo proceso (como hoy). Con más procesos, dos pedidos simultáneos
  podrían agendar el mismo día. La solución en PostgreSQL es una restricción de exclusión sobre `daterange(fecha_inicio,
  fecha_fin, '[]')`; no la agregué porque no pude probarla sin Postgres.
- **Cobrar de más tampoco lo garantiza la base de datos**, solo el código dentro de un candado del proceso (igual que
  la agenda única): alcanza con un solo proceso. Con más, dos cobros simultáneos podrían pasarse del total.
- **El sistema no emite recibos ni facturas** ni se integra con ARCA/AFIP: solo registra los pagos recibidos (Q-10).
- No hay aviso cuando un trabajo se pasa de su fecha de fin sin terminarse (Q-08).
- **Las migraciones `0002` a `0007` no fueron probadas contra PostgreSQL** (la `0005` además crea un índice único
  parcial, que Postgres soporta, pero con otra sintaxis que SQLite) (no había Postgres disponible). Los tests la cubren en
  SQLite. Probarla contra una copia de la base de Neon antes de tocar datos reales.
- `/api/asistente/presupuesto` sin límite de uso (costo de Gemini).
- `limites.js` del frontend no replica los topes nuevos de importe e ítems (el backend responde con un mensaje legible).
- Los nombres de modelos de Gemini por defecto no fueron verificados por mí; el código cae a `gemini-flash-latest`.
- Los tests muestran un aviso de deprecación de Starlette sobre `httpx` (`httpx2`); no afecta el resultado.
