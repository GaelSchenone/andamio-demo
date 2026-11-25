// Comparar textos como los compara una persona: sin tildes, sin mayúsculas y sin espacios de más.
export const normalizar = (texto = '') =>
  texto
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()

// ¿Contiene `texto` todas las palabras de `busqueda`, en cualquier orden? ("alamos los" encuentra "Los Álamos")
export function coincide(texto, busqueda) {
  const palabras = normalizar(busqueda).split(' ').filter(Boolean)
  const base = normalizar(texto)
  return palabras.length > 0 && palabras.every((p) => base.includes(p))
}
