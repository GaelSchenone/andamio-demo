// Enlaces para usar el celular en obra: llamar y llegar.

export const urlTelefono = (telefono) => `tel:${telefono.replace(/[^\d+]/g, "")}`;

// El enlace solo se abre si la persona lo toca: recién ahí la dirección llega a Google Maps.
export const urlMapa = (direccion) =>
  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(direccion)}`;
