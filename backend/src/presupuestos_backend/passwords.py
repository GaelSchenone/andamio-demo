"""Contraseñas: se guardan solo como hash Argon2id (nunca la contraseña en sí)."""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

LARGO_MINIMO = 10
LARGO_MAXIMO = 128

_hasher = PasswordHasher()

# Hash de una contraseña que nadie conoce. Se verifica contra él cuando el usuario no existe,
# así responder "usuario inexistente" tarda lo mismo que "contraseña incorrecta".
HASH_FALSO = _hasher.hash(secrets.token_hex(32))


def hashear(password: str) -> str:
    return _hasher.hash(password)


def verificar(password: str, hash_guardado: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, password)
    except (VerificationError, InvalidHashError):
        return False


def necesita_rehash(hash_guardado: str) -> bool:
    """True si el hash se hizo con parámetros más débiles que los actuales."""
    return _hasher.check_needs_rehash(hash_guardado)
