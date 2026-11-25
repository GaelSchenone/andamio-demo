const BASE = "/api";

class ApiError extends Error {
  constructor(mensaje, status) {
    super(mensaje);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    credentials: "include",
    headers: options.body ? { "Content-Type": "application/json" } : undefined,
    ...options,
  });

  if (!res.ok) {
    let mensaje =
      res.status === 401
        ? "Tu sesión venció. Volvé a ingresar."
        : "Algo no funcionó. Revisá tu conexión y probá de nuevo.";
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") mensaje = data.detail;
    } catch {
      // sin cuerpo JSON: se usa el mensaje genérico
    }
    throw new ApiError(mensaje, res.status);
  }

  if (res.status === 204) return null;
  return res.json();
}

const enJson = (metodo, datos) => ({ method: metodo, body: JSON.stringify(datos) });

export const api = {
  // Sesión
  yo: () => request("/auth/yo"),
  login: (usuario, password) => request("/auth/login", enJson("POST", { usuario, password })),
  logout: () => request("/auth/logout", { method: "POST" }),
  cambiarPassword: (password_actual, password_nueva) =>
    request("/auth/cambiar-password", enJson("POST", { password_actual, password_nueva })),

  // Usuarios (solo dueño)
  listarUsuarios: () => request("/usuarios"),
  crearUsuario: (datos) => request("/usuarios", enJson("POST", datos)),
  editarUsuario: (id, cambios) => request(`/usuarios/${id}`, enJson("PATCH", cambios)),
  restablecerPassword: (id, password_nueva) =>
    request(`/usuarios/${id}/password`, enJson("POST", { password_nueva })),

  // Clientes y obras (leer: todos; escribir: solo dueño)
  listarClientes: (buscar) =>
    request(`/clientes${buscar ? `?buscar=${encodeURIComponent(buscar)}` : ""}`),
  obtenerCliente: (id) => request(`/clientes/${id}`),
  crearCliente: (datos) => request("/clientes", enJson("POST", datos)),
  actualizarCliente: (id, datos) => request(`/clientes/${id}`, enJson("PUT", datos)),
  eliminarCliente: (id) => request(`/clientes/${id}`, { method: "DELETE" }),
  crearObra: (clienteId, datos) => request(`/clientes/${clienteId}/obras`, enJson("POST", datos)),
  actualizarObra: (id, datos) => request(`/obras/${id}`, enJson("PUT", datos)),
  eliminarObra: (id) => request(`/obras/${id}`, { method: "DELETE" }),

  // Presupuestos
  listarPresupuestos: (buscar) =>
    request(`/presupuestos${buscar ? `?buscar=${encodeURIComponent(buscar)}` : ""}`),
  obtenerPresupuesto: (id) => request(`/presupuestos/${id}`),
  crearPresupuesto: (datos) => request("/presupuestos", enJson("POST", datos)),
  actualizarPresupuesto: (id, datos) => request(`/presupuestos/${id}`, enJson("PUT", datos)),
  eliminarPresupuesto: (id) => request(`/presupuestos/${id}`, { method: "DELETE" }),
  urlPdf: (id) => `${BASE}/presupuestos/${id}/pdf`,
  cambiarEstadoPresupuesto: (id, estado) =>
    request(`/presupuestos/${id}/estado`, enJson("PUT", { estado })),
  pasarATrabajo: (id) => request(`/presupuestos/${id}/trabajo`, { method: "POST" }),

  // Trabajos (ver: todos, sin precios; crear y cancelar: solo dueño)
  // `desde` y `hasta` (YYYY-MM-DD) piden solo los trabajos que caen en ese rango, para el calendario.
  listarTrabajos: ({ incluirCancelados = false, desde, hasta } = {}) => {
    const params = new URLSearchParams();
    if (incluirCancelados) params.set("incluir_cancelados", "true");
    if (desde) params.set("desde", desde);
    if (hasta) params.set("hasta", hasta);
    const consulta = params.toString();
    return request(`/trabajos${consulta ? `?${consulta}` : ""}`);
  },
  // `dias`: los días en que se trabaja (AAAA-MM-DD), no hace falta que sean seguidos.
  agendarTrabajo: (id, dias) => request(`/trabajos/${id}/agendar`, enJson("POST", { dias })),
  reprogramarTrabajo: (id, datos) => request(`/trabajos/${id}/reprogramar`, enJson("POST", datos)),
  terminarTrabajo: (id) => request(`/trabajos/${id}/terminar`, { method: "POST" }),
  cancelarTrabajo: (id) => request(`/trabajos/${id}/cancelar`, { method: "POST" }),

  // Cobros (solo dueño: el empleado nunca ve plata)
  cobrosDeTrabajo: (id) => request(`/trabajos/${id}/cobros`),
  registrarCobro: (id, datos) => request(`/trabajos/${id}/cobros`, enJson("POST", datos)),
  anularCobro: (id) => request(`/cobros/${id}/anular`, { method: "POST" }),
  cobrosPendientes: () => request("/cobros/pendientes"),

  // Agente de ayuda (chat que consulta datos, solo lectura)
  estadoAgente: () => request("/agente/estado"),
  // `conversacionId`: con el webhook, el servidor devuelve un id y hay que reenviarlo para seguir la charla.
  chatAgente: (mensajes, conversacionId = null) =>
    request("/agente/chat", enJson("POST", { mensajes, conversacion_id: conversacionId })),

  // Asistente IA
  estadoAsistente: () => request("/asistente/estado"),
  completarConIA: (mensaje) => request("/asistente/presupuesto", enJson("POST", { mensaje })),
};

export { ApiError };
