# Decisiones de negocio

Registro de las reglas de negocio que el sistema ya aplica, de **quién las decidió** y de **qué falta validar**.
Existe porque varias salieron de una conversación entre el autor y el asistente, y no de una charla con el dueño
del negocio. Antes de usar el sistema con clientes reales, el dueño tiene que revisarlas.

## Estados
- **Aprobada (provisoria):** el autor la aprobó. El dueño todavía no la vio.
- **Propuesta:** la sugirió el asistente y está implementada, pero nadie la confirmó de forma explícita.
- **Validada:** el dueño la confirmó. *(Ninguna lo está todavía.)*

Cuando el dueño revise una, cambiar su estado a "Validada", anotar la fecha y, si pidió un cambio, abrir una
tarea para ajustarla. La columna "Si cambia" dice qué hay que tocar.

## Decisiones tomadas

| Nº | Decisión | Estado | Quién y cuándo | Si cambia |
|---|---|---|---|---|
| D-01 | **Permisos del empleado:** ve la agenda y los trabajos, cambia el estado de un trabajo y ve clientes y direcciones. **No ve precios, presupuestos ni cobros**, y no gestiona usuarios. El dueño puede todo. | Aprobada (provisoria) | el autor, 2026-11-19 | `permisos.py` (un solo lugar) |
| D-02 | Para **aprobar** un presupuesto hace falta elegir cliente **y** obra. | Aprobada (provisoria) | el autor, 2026-11-19 | `crud.cambiar_estado` |
| D-03 | Un presupuesto **aprobado no se edita ni se borra**; hay que pasarlo a otro estado primero. | Aprobada (provisoria) | el autor, 2026-11-19 | `crud.actualizar_presupuesto`, `crud.eliminar_presupuesto` |
| D-04 | Con un **trabajo vigente** no se le puede sacar la aprobación al presupuesto: primero se cancela el trabajo. | Aprobada (provisoria) | el autor, 2026-11-19 | `crud.cambiar_estado` |
| D-05 | Un presupuesto tiene a lo sumo **un trabajo vigente** (garantizado por la base). Un trabajo se cancela mientras no empezó: "por agendar" o "agendado" (la ampliación a "agendado" la pidió el autor después, ver D-15). | Aprobada (provisoria) | el autor, 2026-11-19 | `crud_trabajos`, índice `uq_trabajo_vigente_por_presupuesto` |
| D-06 | No se borra un **cliente con obras**, ni un cliente u obra **con presupuestos asociados**. | Aprobada (provisoria) | el autor, 2026-11-19 | `crud_clientes` |
| D-07 | Los presupuestos que ya existían quedaron como **borrador** y sin cliente ni obra. | Aprobada (provisoria) | el autor, 2026-11-19 | migración `0005` (ya aplicada: habría que corregir datos) |
| D-08 | Al elegir un cliente u obra, su nombre y dirección se **copian** al presupuesto como foto del momento: si después cambian, los PDF ya emitidos no se alteran. | Aprobada (provisoria) | el autor, 2026-11-19 | `NuevoPresupuesto.jsx` |
| D-09 | Hay **dos repos**: `andamio` (real, privado) y `andamio-demo` (datos ficticios, público, para la entrega del curso). | Aprobada | el autor, 2026-11-19 | roadmap |
| D-10 | Datos que se guardan de un **cliente**: nombre, tipo (casa o consorcio), teléfono y notas. De una **obra**: dirección, referencia y notas. | Propuesta | Asistente (mínimo por Ley 25.326); sin confirmar | `models.Cliente`, `models.Obra` y migración |
| D-11 | **Usuarios:** no se borran, se desactivan; siempre queda al menos un dueño activo; el primer dueño sale de variables de entorno; el dueño le restablece la contraseña a quien la olvide. | Propuesta | Asistente | `crud_usuarios`, `bootstrap` |
| D-12 | **Seguridad de acceso:** contraseña de 10+ caracteres; tras 5 intentos fallidos desde una IP se bloquea 15 minutos; la sesión dura 30 días. | Propuesta | Asistente | `auth.py`, `passwords.py` |
| D-13 | **Agenda única:** dos trabajos no pueden compartir ningún día (el primero y el último cuentan). Un trabajo que termina el 10 y otro que empieza el 11 no se pisan. Los cancelados y los "por agendar" no ocupan lugar; **uno terminado sigue ocupando sus días**. | Propuesta | Asistente; responde a Q-01, sin confirmar | `crud_trabajos._verificar_agenda_libre` (único lugar) |
| D-14 | **Días corridos:** no hay regla de sábados, domingos ni feriados. El calendario marca los fines de semana pero no los bloquea. Un trabajo dura como máximo 366 días. | Propuesta | Asistente; responde a Q-02, sin confirmar | `crud_trabajos._validar_fechas` y el calendario del frontend |
| D-15 | **Ciclo del trabajo:** por agendar → agendado → en curso → terminado. Se puede **cancelar mientras no empezó** (por agendar o agendado; **amplía D-05**) y al cancelar las fechas quedan libres. Se puede terminar un trabajo agendado aunque nadie lo haya marcado como iniciado. | **Cancelar un trabajo ya agendado: aprobada (provisoria). Un trabajo en curso NO se cancela: confirmado por el autor, 2026-11-19.** El resto del ciclo: propuesta | el autor pidió poder cancelar un trabajo agendado, 2026-11-19; el resto, asistente | `crud_trabajos` |
| D-16 | **Reprogramar:** solo un trabajo agendado o en curso; se puede reagendar **por el motivo que sea**: hay que elegir una **causa** (clima, cliente, materiales u otra) pero el **detalle escrito es opcional**; queda un historial con fechas anteriores y nuevas, quién lo hizo y cuándo. Un trabajo en curso solo puede cambiar su fecha de fin. | **Reagendar sin pedir explicaciones: aprobada (provisoria).** El resto: propuesta | el autor, 2026-11-19 (motivo libre); el resto, asistente, responde a Q-03 sin confirmar | `crud_trabajos.reprogramar`, `schemas_trabajos.ReprogramarIn` |
| D-17 | **Quién hace qué en el calendario:** el dueño agenda, reprograma, cancela y ve el historial de cambios. El dueño y el empleado inician y terminan trabajos. | Propuesta | Asistente, apoyada en D-01 | `routers/trabajos.py`, `permisos.py` |
| D-18 | Los **cobros son siempre en dos partes: 50% de seña y 50% de saldo**. El sistema sugiere esos montos (la mitad se redondea al centavo; el saldo es lo que falta). | Aprobada (provisoria) | el autor, 2026-11-19 ("siempre 50 y 50") | `crud_cobros.resumen` |
| D-19 | Se aceptan montos distintos a la mitad, pero la suma de cobros vigentes **nunca supera el total** del presupuesto. | Propuesta | Asistente | `crud_cobros.registrar` |
| D-20 | **"Cobrado" = terminado y pagado por completo.** Si ya estaba todo pagado al terminarlo, pasa directo; si se anula un cobro de un trabajo cobrado, vuelve a "terminado". | Propuesta | Asistente | `crud_cobros.recalcular_estado` |
| D-21 | Un cobro **no se edita ni se borra**: se **anula** (queda quién y cuándo) y deja de contar. | Propuesta | Asistente | `crud_cobros.anular` |
| D-22 | **No se cancela un trabajo con cobros vigentes**: primero se anulan (por ejemplo, al devolver la seña). | Propuesta | Asistente | `crud_trabajos.cancelar` |
| D-23 | La seña **no bloquea** iniciar un trabajo: solo se ve qué falta cobrar. | Propuesta | Asistente | no hay regla que cambiar: habría que agregarla en `crud_trabajos.iniciar` |
| D-24 | **Solo el dueño ve y maneja los cobros.** El empleado nunca ve plata, ni siquiera saldos en los trabajos. | Aprobada (provisoria) | el autor, 2026-11-19 (D-01) | `permisos.py`, `schemas_trabajos` |
| D-25 | La **fecha de un cobro no puede ser futura**. | Propuesta | Asistente | `crud_cobros.registrar` |
| D-26 | **Presupuestos anteriores:** lo que existe son solo PDFs (no hay base de datos que migrar). No se importan automáticamente; se conservan como archivo y, si algún trabajo sigue vigente, se vuelve a cargar a mano. Se decide **cuando el autor apruebe la app final**. Los PDFs de clientes nunca van al repo. | Aprobada | el autor, 2026-11-19 | `.gitignore` (bloquea los `.pdf`) |
| D-27 | **Identidad visual "cinta de obra":** claro u oscuro según el sistema (sin selector manual), blanco y negro con **un solo acento amarillo** (botón principal, sección activa y día de hoy), íconos de línea, tipografías Inter y Barlow Condensed autohospedadas. Los estados nunca se comunican solo con color. | Aprobada (provisoria) | el autor, 2026-11-19 | `frontend/src/styles/tokens.css` (un test exige contraste mínimo y que no haya colores fuera de ahí) |
| D-28 | **Navegación por rol:** el dueño ve Inicio, Trabajos, Presupuestos, Cobros, Clientes y Ajustes; el empleado ve Inicio, Trabajos, Clientes y Ajustes. En celular, barra inferior (con "Más" solo para el dueño). Las rutas prohibidas redirigen a Inicio; la seguridad real sigue en el servidor. | Aprobada (provisoria) | el autor, 2026-11-19 | `frontend/src/layout/navegacion.js` (+ test) |
| D-29 | **Detalle junto a la lista** en pantallas anchas; en celular, a pantalla completa. **Trabajos abre en calendario** (mes o semana) con la lista de todos los trabajos al costado mientras no haya uno elegido; la lista completa es otra vista. Las tareas cortas van en ventana (hoja desde abajo en celular). | Aprobada (provisoria) | el autor, 2026-11-19 | `frontend/src/pages/Trabajos/`, `frontend/src/layout/MaestroDetalle.jsx` |
| D-30 | **Un trabajo puede hacerse en días que no son seguidos** (por ejemplo 13, 14, 26 y 27). Se eligen día por día en el calendario; el trabajo guarda su primer y último día y los días del medio en que no se trabaja, y la agenda única solo cuenta los días trabajados. Un trabajo de corrido sigue funcionando igual. Los cambios de fecha del historial siguen mostrando solo primer y último día. | Aprobada (provisoria) | el autor, 2026-11-19 | `crud_trabajos.dias_trabajados`, tabla `trabajo_dias_sin_trabajo` (migración 0008) |
| D-31 | **Ayudante con IA (chat con la orbe):** solo **consulta y guía**, no modifica nada (si hay que hacer algo, explica y ofrece un botón para ir a la pantalla). Usa los **mismos permisos** que quien habla: a la empleada no se le ofrecen presupuestos, cobros ni precios. A Gemini solo le salen **nombre, tipo y direcciones** de los clientes, **nunca teléfono ni notas**; los trabajos salen sin importes. Se puede dictar por voz con el navegador (Chrome y Edge mandan ese audio a su propio servicio de voz). Funciona con **Gemini** (con herramientas) o, si está definida `AGENTE_WEBHOOK_URL`, con un **agente de Copilot Studio por webhook** de Power Automate: ese agente no tiene herramientas, así que el backend le manda adentro del mensaje la guía y los datos que la pregunta necesita (los mismos mínimos, con los permisos del usuario; los datos viajan a Microsoft). El **"Completar con IA" de presupuestos** usa el mismo motor, y **no completa ni elige cliente ni obra** (los elige una persona de la lista): así la IA no puede poner ni crear un cliente equivocado. Se limita a 20 mensajes cada 5 minutos por usuario y no se registra el contenido de las conversaciones. Falta la autorización para tratar datos de clientes con Gemini (Q-07). | Aprobada (provisoria) | el autor, 2026-11-20 | `agente.py`, `agente_guia.py`, `routers/agente.py`, `frontend/src/layout/agente/` |

## Preguntas abiertas (para el dueño del negocio)

| Nº | Pregunta | Por qué importa |
|---|---|---|
| Q-01 | ¿Alguna vez hace **dos trabajos chicos el mismo día**? | Define si la agenda puede tener trabajos superpuestos. Mientras tanto rige D-13 (no se pueden pisar). |
| Q-02 | ¿**Trabaja los sábados**? ¿Y feriados? | Cómo se cuentan los días de un trabajo de varios días. Mientras tanto rige D-14 (días corridos, sin bloquear fines de semana). |
| Q-03 | ¿Qué se hace cuando **llueve** y la obra es exterior? | Reglas de reprogramación. Mientras tanto rige D-16 (se reprograma eligiendo la causa "clima", con detalle opcional y sin reglas automáticas). |
| Q-04 | ¿Qué otros datos del cliente quiere guardar (mail, CUIT, razón social del consorcio)? | Cada dato nuevo es un dato personal más (Ley 25.326). |
| Q-05 | ¿Los **cobros** son siempre 50% y 50%? | el autor respondió que sí (D-18); falta que el dueño lo confirme. Si hay excepciones (obras chicas pagadas de una vez, anticipos mayores), el sistema ya acepta otros montos. |
| Q-06 | ¿El empleado debería poder **ver el teléfono** del cliente? | Hoy lo ve (D-01); es un dato personal. |
| Q-07 | ¿Quién es **responsable** de la base de datos de clientes? | Ley 25.326: hay que definirlo antes de cargar datos reales. |
| Q-08 | ¿Cómo quiere enterarse de que un trabajo **se pasó de su fecha de fin** sin terminarse? | Hoy no hay ningún aviso: un trabajo agendado sigue "agendado" aunque la fecha ya pasó. |
| Q-09 | ¿Necesita registrar **cómo** le pagan (efectivo, transferencia, otro)? | Hoy solo hay una nota libre en cada cobro; un campo propio permitiría reportes. |
| Q-10 | ¿Necesita **emitir recibos o facturas** desde el sistema? | Hoy no se emiten comprobantes ni hay integración con ARCA/AFIP: es un tema legal y fiscal que conviene consultar con su contador antes de diseñarlo. |

## Pendiente fuera de lo funcional
- Confirmar el tratamiento de datos personales (incluido lo que se envía a Gemini) con el área que corresponda.
  Ver `docs/architecture.md`, sección "Seguridad y datos personales".
