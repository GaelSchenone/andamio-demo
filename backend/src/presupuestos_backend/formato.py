"""Helpers de formato en español/Argentina, compartidos por el PDF y la API."""

import datetime as dt
from decimal import Decimal


def moneda(valor: Decimal | float | int) -> str:
    """1234.5 -> '1.234,50' (formato de pesos argentinos, sin el símbolo $)."""
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


def fecha_larga(fecha: dt.date) -> str:
    return fecha.strftime("%d/%m/%Y")
