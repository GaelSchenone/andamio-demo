# Flujos de negocio

Hoy la agenda de una empresa de reparaciones se coordina por **WhatsApp**. Este sistema ordena ese flujo.

## Flujo completo (objetivo)
```
Cliente consulta → Presupuesto → Aprobación → Trabajo agendado → Ejecución → Cobro
```

## 1. Presupuesto — IMPLEMENTADO
1. Se abre "Nuevo presupuesto" y se cargan cliente/obra, dirección, ítems (descripción, unidad, cantidad, importe),
   plazo, forma de pago, materiales y observaciones.
2. **Opcional, asistente IA:** se pega el mensaje del cliente o notas coloquiales; Gemini devuelve un borrador que
   rellena el formulario. El importe lo completa solo si el texto trae un precio; nunca lo estima.
3. Se guarda; el total es la suma de los importes de los ítems.
4. Se descarga el PDF (`/api/presupuestos/{id}/pdf`).
5. En "Historial" se busca por cliente/obra, se edita o se elimina.

## 2. Clientes y obras — IMPLEMENTADO
1. **Pestaña "Clientes"** (dueño y empleado): lista ordenada por nombre, con teléfono y cantidad de obras.
   Se busca por nombre, teléfono o dirección de cualquiera de sus obras.
2. **Detalle de un cliente:** datos, notas y sus obras. El teléfono es un enlace para llamar y cada obra tiene
   "Cómo llegar" (abre Google Maps; la dirección solo sale de la app si la persona toca el enlace).
3. **Solo el dueño** crea, edita o borra clientes y obras. El empleado solo consulta.
4. Para borrar un cliente primero hay que borrar sus obras.
5. Al crear un presupuesto se puede elegir un cliente registrado y una de sus obras (ver sección 3).

## 3. Aprobación y pase a trabajo — IMPLEMENTADO
1. **Elegir cliente y obra:** en el formulario del presupuesto hay un selector de cliente registrado y, una vez
   elegido, de una de sus obras. Al elegirlos se copian el nombre y la dirección al presupuesto (el dueño puede
   retocarlos). También se pueden escribir a mano, pero así el presupuesto no se puede aprobar.
2. **Estado del presupuesto** (desde el Historial): borrador, enviado, aprobado o rechazado. Se mueve libremente
   entre ellos con estas excepciones: **aprobar exige cliente y obra**; un **aprobado no se edita ni se borra**; y si
   ya tiene un trabajo vigente, hay que cancelar el trabajo antes de cambiarle el estado.
3. **Pasar a trabajo:** en el Historial, un presupuesto aprobado muestra el botón "Pasar a trabajo". El trabajo
   queda "por agendar" y se ve en la pestaña **Trabajos**. Un presupuesto no puede tener dos trabajos vigentes.
4. **Pestaña Trabajos** (dueño y empleado): cliente, dirección con "Cómo llegar", teléfono, las tareas, plazo y quién
   pone los materiales. **Sin precios**, para que el empleado los pueda ver. Solo el dueño puede cancelar un trabajo
   mientras no empezó (ver sección 4); al cancelarlo, el presupuesto sigue aprobado y se puede volver a pasar a trabajo.
5. **Presupuestos que ya existían:** quedaron como borrador y sin cliente ni obra. Para aprobarlos hay que editarlos
   y elegir cliente y obra primero.

## 4. Calendario — IMPLEMENTADO
Todo esto parte de supuestos que el dueño todavía no validó (ver `docs/decisiones.md`, D-13 a D-17).
1. **Pestaña Trabajos, con dos vistas:** "Lista" (primero lo que está en curso, después lo que viene, después lo que
   falta agendar) y "Calendario" (grilla mensual de lunes a domingo; los fines de semana se marcan; al tocar un día se
   ven abajo sus trabajos).
2. **Agendar** (dueño): un trabajo "por agendar" recibe fecha de inicio y de fin. Si esos días se superponen con otro
   trabajo, el sistema lo rechaza y dice con cuál (cliente, dirección y fechas). Días seguidos sin compartir ninguno
   están permitidos.
3. **Iniciar y terminar** (dueño y empleado, desde la obra): "Iniciar" pasa de agendado a en curso; "Terminar" cierra el
   trabajo (también se puede terminar uno agendado si se olvidaron de iniciarlo).
4. **Reprogramar** (dueño): cambia las fechas por el motivo que sea: se elige una causa (clima, cliente,
   materiales u otra) y el detalle escrito es opcional. Queda registrado quién lo hizo y cuándo, y se ve en "Cambios de fecha". Un trabajo ya en curso solo puede
   cambiar la fecha de fin.
5. **Cancelar** (dueño): mientras el trabajo no empezó. Las fechas quedan libres para otro. El presupuesto sigue
   aprobado y se puede volver a pasar a trabajo.
6. **Lo que no hace todavía:** no avisa si un trabajo se pasa de su fecha de fin (Q-08) ni maneja cobros: "cobrado"
   llega con el punto 5.

## 5. Cobros — IMPLEMENTADO
Solo lo ve y maneja el dueño. El negocio cobra siempre en dos partes: **50% de seña y 50% de saldo**.
1. **Registrar un cobro:** en un trabajo, botón "Cobros". Se elige el concepto (seña o saldo), el monto, la fecha en que
   se recibió el pago y una nota opcional (por ejemplo "efectivo" o "transferencia"). El sistema **propone** el monto: la
   mitad del total para la seña (con redondeo al centavo) y todo lo que falta para el saldo. Se puede escribir otro.
2. **Nunca se cobra de más:** si el monto supera lo que falta, el sistema lo rechaza y dice cuánto falta.
3. **Cobrado:** cuando el trabajo está terminado y pagado por completo, pasa a "cobrado". Si ya estaba todo pagado al
   terminarlo, pasa directo.
4. **Corregir un error:** un cobro no se edita ni se borra. Se **anula** (queda quién y cuándo) y deja de contar. Si el
   trabajo estaba cobrado, vuelve a "terminado".
5. **Cancelar un trabajo con cobros:** no se puede mientras haya cobros vigentes. Si hay que devolver la seña, primero
   se anula ese cobro.
6. **Pestaña Cobros:** "Falta cobrar en total" y, trabajo por trabajo, cuánto se cobró y cuánto falta. Primero los
   trabajos ya terminados (esos se deben ya). Desde ahí también se registran cobros.
7. **El empleado nunca ve plata:** ni los cobros, ni los saldos, ni en la pestaña Trabajos.
8. **Lo que no hace:** no emite recibos ni facturas ni se conecta con ARCA/AFIP (Q-10), y no registra el medio de pago
   más que como nota libre (Q-09).

## 6. Acceso — IMPLEMENTADO
1. **Primer arranque:** el dueño se crea solo, desde `DUENO_USUARIO` y `DUENO_PASSWORD`, si no hay ningún usuario.
2. **Entrar:** usuario y contraseña. Tras 5 intentos fallidos desde una IP, se bloquea 15 minutos.
3. **Pantalla "Usuarios" (solo dueño):** crear usuarios (dueño o empleado), cambiar rol, desactivar o reactivar,
   y ponerle una contraseña nueva a alguien. Los usuarios no se borran, se desactivan.
4. **Pantalla "Cuenta" (todos):** cambiar la propia contraseña. Se cierran las demás sesiones abiertas.
5. **Si alguien olvida su contraseña:** el dueño se la cambia desde "Usuarios".
   **Si la olvida el único dueño:** el autor la recupera con `usuarios_cli password` (ver `CLAUDE.md`).
6. Siempre tiene que haber al menos un dueño activo: el sistema no deja desactivarlo ni bajarlo de rol.
7. **Qué ve cada rol:** el dueño, todo. El empleado, solo Agenda y Cuenta (y, cuando existan, clientes y
   direcciones, y el cambio de estado de un trabajo). No ve precios, presupuestos ni cobros.
