# Roadmap

## Hecho (heredado de `none-hogar-presupuestos`)
- Presupuestos con ítems y PDF
- Login con clave compartida
- Asistente IA con Gemini y mensajes de validación en castellano

## Fase 0 — Base sólida (antes de agregar entidades)
- [x] Migraciones con Alembic (base idempotente + `0002`)
- [x] Importes en `Numeric(14, 2)` y suma con `Decimal`
- [x] Datos de contacto fuera del código (variables `NEGOCIO_*`)
- [x] Tests con pytest (57): dinero, auth, límite de login, API, PDF y migraciones
- [x] Auth endurecida: `SECRET_KEY` y `ACCESS_CODE` obligatorias en producción, comparación en tiempo constante, límite de intentos
- [x] Dos bugs corregidos que aparecieron al testear (cookie inválida → 500; nombre de PDF con tildes → header roto)
- [ ] **Probar la migración `0002` contra una copia de la base de Neon** (no había Postgres para probarla)
- [ ] **Presupuestos anteriores:** hoy son solo PDFs, no hay una base de datos que migrar. No se importan solos: se
  conservan como archivo y, si algún trabajo sigue vigente, se vuelve a cargar a mano. Se decide cuando el autor apruebe la
  app final (D-26). Esos PDFs tienen datos de clientes: nunca van al repo (el `.gitignore` bloquea los `.pdf`).
- [ ] Completar `NEGOCIO_*` en el `.env` real: sin eso el PDF sale sin celular ni Instagram
- [x] Primer commit del repo (local)
- [ ] Push a GitHub (repo **privado**; requiere `gh auth login`)
- [ ] **Al desplegar:** definir `SECRET_KEY` (32+ caracteres) y `DUENO_USUARIO` / `DUENO_PASSWORD` en el hosting.
  `ACCESS_CODE` ya no existe, y las sesiones de la versión anterior quedan invalidadas (hay que volver a entrar).

## Fase 1 — MVP (lo que tiene que andar sí o sí)
1. [x] **Usuarios** con roles dueño y empleado (reemplaza la clave compartida): login, pantallas "Usuarios" y
   "Cuenta", permisos por rol, primer dueño por variables de entorno, línea de comandos. 117 tests.
2. [x] **Clientes y obras**: alta, edición, borrado y búsqueda; el empleado solo consulta. Incluyó cerrar una fuga
   de datos: el log de acceso guardaba lo que se buscaba. 163 tests.
3. [x] **Presupuesto → Trabajo:** estados del presupuesto, vínculo con cliente y obra, pase a trabajo ("por agendar")
   y pestaña Trabajos sin precios para el empleado. 204 tests. Las reglas las aprobó el autor de forma
   provisoria; falta validarlas con el dueño (ver `docs/decisiones.md`).
4. [x] **Calendario** de agenda única con estados y reprogramación con historial: agendar sin superponer, iniciar,
   terminar, cancelar, reprogramar con causa y motivo, vista de lista y de calendario. 261 tests. Parte de supuestos
   del asistente sobre las preguntas Q-01 a Q-03 (ver `docs/decisiones.md`, D-13 a D-17).
5. [x] **Cobros:** seña y saldo (siempre 50 y 50), nunca de más, anulación en lugar de borrado, paso a "cobrado", y una
   pestaña con lo que falta cobrar. 309 tests. **Con esto queda completo el MVP de la Fase 1.**

## Fase 2 — Después del MVP (fuera de alcance por ahora)
- Aviso por WhatsApp (link con mensaje armado, sin API oficial) como primer paso
- Sincronización con Google Calendar (requiere OAuth)
- Más de un equipo en paralelo (hoy es agenda única)
- Límite de uso del asistente IA y revisión de clave paga de Gemini
- Reportes de cobros y de trabajos por período

## Repo `andamio-demo` — para la entrega del curso
Se arma **cuando el real esté usable**, como copia con todo ficticio:
- Datos de prueba generados, sin clientes ni contacto reales; marca y datos de contacto neutros
- Repo **público**, sin credenciales ni historial con datos reales (partir de un historial limpio)
- Entregables de la consigna: `spec.md`, informe de QA, `README.md` con links a front y back en producción
- Despliegue en internet: front (Netlify o Vercel), back (Render) y Postgres (Neon), todo por variables de entorno
- Fecha límite de la plataforma: 31 de diciembre
