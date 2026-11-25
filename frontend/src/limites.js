// Los mismos límites que valida el backend (backend/.../schemas.py, PresupuestoIn e ItemIn).
// Si cambian allá, hay que cambiarlos acá.
export const LARGO_MAXIMO = {
  cliente_obra: 200,
  direccion: 300,
  plazo_obra: 200,
  forma_pago: 300,
  observaciones: 2000,
  descripcion: 500,
  unidad: 50,
};

export const VIGENCIA_MAXIMA = 365;
