// Animación del asistente IA: "tipea" una lista de valores en cascada, como si alguien
// estuviera completando el formulario en vivo.

const ESCALON_MS = 110; // demora entre que arranca un campo y el siguiente
const MS_POR_LETRA = 12;
const MAX_MS_CAMPO = 700;

// pasos: [{ clave, final, tipear? }]. onFrame recibe un Map clave -> valor parcial con
// los pasos que ya arrancaron. Devuelve una promesa que se resuelve al terminar.
export function animarPasos(pasos, onFrame) {
  const sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const planes = pasos.map((paso, i) => ({
    ...paso,
    texto: String(paso.final),
    inicio: i * ESCALON_MS,
    duracion:
      paso.tipear === false ? 0 : Math.min(MAX_MS_CAMPO, String(paso.final).length * MS_POR_LETRA),
  }));
  const fin = Math.max(0, ...planes.map((p) => p.inicio + p.duracion));

  return new Promise((resolve) => {
    let t0 = null;
    function frame(ahora) {
      t0 ??= ahora;
      const t = sinMovimiento ? Infinity : ahora - t0;
      const valores = new Map();
      for (const p of planes) {
        if (t < p.inicio) continue;
        const avance = p.duracion ? Math.min(1, (t - p.inicio) / p.duracion) : 1;
        valores.set(
          p.clave,
          avance === 1 ? p.final : p.texto.slice(0, Math.ceil(p.texto.length * avance))
        );
      }
      onFrame(valores);
      if (t >= fin) resolve();
      else requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  });
}

// Lleva la pantalla de a poco hacia el campo que se está completando, cuadro a cuadro.
// No usa scrollIntoView({ behavior: "smooth" }) porque Chrome corta esa animación cada
// vez que se vuelve a llamar, y acá se llama cada ~100 ms. Si el usuario scrollea a
// mano, deja de seguir para no pelearle.
export function crearSeguimiento() {
  const EVENTOS_MANUALES = ["wheel", "touchstart", "keydown"];
  let objetivo = 0;
  let cuadro = null;

  function paso() {
    const restante = objetivo - window.scrollY;
    if (Math.abs(restante) < 1) {
      detener();
      return;
    }
    const avance = Math.sign(restante) * Math.max(1, Math.abs(restante) * 0.12);
    window.scrollTo(0, window.scrollY + avance);
    cuadro = requestAnimationFrame(paso);
  }

  function detener() {
    if (cuadro !== null) cancelAnimationFrame(cuadro);
    cuadro = null;
    for (const evento of EVENTOS_MANUALES) window.removeEventListener(evento, detener);
  }

  function arrancar() {
    for (const evento of EVENTOS_MANUALES) {
      window.addEventListener(evento, detener, { passive: true });
    }
    cuadro = requestAnimationFrame(paso);
  }

  return {
    // Si el elemento ya se ve entre las pestañas y la barra del total (que son fijas),
    // no mueve nada; si no, lo lleva al centro de esa franja.
    mostrar(elemento) {
      if (!elemento) return;
      const arriba = document.querySelector(".shell-superior")?.getBoundingClientRect().bottom ?? 0;
      const abajo =
        window.innerHeight - (document.querySelector(".editor-resumen--fijo")?.offsetHeight ?? 0);
      const { top, bottom } = elemento.getBoundingClientRect();
      if (top >= arriba && bottom <= abajo) return;

      const maximo = document.documentElement.scrollHeight - window.innerHeight;
      const centro = (top + bottom) / 2 - (arriba + abajo) / 2;
      objetivo = Math.min(maximo, Math.max(0, Math.round(window.scrollY + centro)));
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        window.scrollTo(0, objetivo);
      } else if (cuadro === null) {
        arrancar();
      }
    },
    detener,
  };
}
