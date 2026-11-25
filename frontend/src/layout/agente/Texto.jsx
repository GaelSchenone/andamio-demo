// Muestra la respuesta del agente: solo entiende lo que suele escribir (negritas con ** y listas con - o *).
// No usa HTML crudo: todo se pone como texto, así nada de lo que venga de la base puede inyectar código.

const conNegritas = (linea) =>
  linea.split(/(\*\*[^*]+\*\*)/g).map((trozo, i) =>
    trozo.startsWith('**') && trozo.endsWith('**') ? <strong key={i}>{trozo.slice(2, -2)}</strong> : trozo
  )

export default function Texto({ texto }) {
  const bloques = []
  let lista = null
  for (const linea of texto.split('\n')) {
    const item = linea.match(/^\s*[-*]\s+(.*)$/)
    if (item) {
      lista ??= []
      lista.push(item[1])
      if (lista.length === 1) bloques.push({ lista })
    } else {
      lista = null
      if (linea.trim()) bloques.push({ parrafo: linea })
    }
  }
  return bloques.map((b, i) =>
    b.lista ? (
      <ul key={i}>
        {b.lista.map((item, j) => (
          <li key={j}>{conNegritas(item)}</li>
        ))}
      </ul>
    ) : (
      <p key={i}>{conNegritas(b.parrafo)}</p>
    )
  )
}
