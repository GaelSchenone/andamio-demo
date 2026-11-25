"""Errores de reglas de negocio: los endpoints los traducen a HTTP con el mismo mensaje."""


class ReglaDeNegocio(Exception):
    """La operación es válida en sí, pero el estado actual de los datos no la permite (HTTP 409)."""


class VinculoInvalido(Exception):
    """El cliente o la obra elegidos no existen o no se corresponden entre sí (HTTP 422)."""
