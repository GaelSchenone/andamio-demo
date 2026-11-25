"""Datos del negocio que salen impresos en el PDF.

Se leen de variables de entorno y NO están escritos en el código: el nombre y el celular
de una persona no deben quedar en un repositorio. Si una variable no está definida, esa
parte simplemente no aparece en el PDF. Se leen en cada uso (no al importar el módulo).
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Negocio:
    nombre: str
    rubro: str
    responsable: str
    telefono: str
    instagram: str

    def lineas_encabezado(self) -> list[str]:
        """Contacto para el encabezado: una línea con responsable y teléfono, otra con Instagram."""
        lineas = []
        principal = " // ".join(p for p in (self.responsable, self.telefono) if p)
        if principal:
            lineas.append(principal)
        if self.instagram:
            lineas.append(f"Instagram: {self.instagram}")
        return lineas

    def linea_pie(self) -> str:
        instagram = f"Instagram {self.instagram}" if self.instagram else ""
        partes = (self.nombre, self.responsable, self.telefono, instagram)
        return " | ".join(p for p in partes if p)


def cargar_negocio() -> Negocio:
    def var(nombre: str, defecto: str = "") -> str:
        return os.environ.get(nombre, defecto).strip()

    return Negocio(
        nombre=var("NEGOCIO_NOMBRE", "Obras Demo"),
        rubro=var("NEGOCIO_RUBRO", "Pintura y reparaciones generales"),
        responsable=var("NEGOCIO_RESPONSABLE"),
        telefono=var("NEGOCIO_TELEFONO"),
        instagram=var("NEGOCIO_INSTAGRAM"),
    )
