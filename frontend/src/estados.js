// Cómo se nombran y se muestran los estados de un trabajo (los usan la lista, el calendario y los cobros).

export const ESTADOS_TRABAJO = {
  por_agendar: "Por agendar",
  agendado: "Agendado",
  en_curso: "En curso",
  terminado: "Terminado",
  cobrado: "Cobrado",
  cancelado: "Cancelado",
};

export const claseDelEstadoDeTrabajo = (estado) =>
  estado === "en_curso" ? "nh-chip--solido" : estado === "cancelado" ? "nh-chip--inactivo" : "";

export const ESTADOS_PRESUPUESTO = {
  borrador: "Borrador",
  enviado: "Enviado",
  aprobado: "Aprobado",
  rechazado: "Rechazado",
};
