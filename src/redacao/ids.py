"""Identificadores UUIDv7 (RFC 9562), decisão D18.

O Python 3.12 não tem `uuid.uuid7()` (chega no 3.14). O formato: 48 bits de timestamp Unix em
milissegundos, a versão (7), 74 bits aleatórios e a variante RFC. O timestamp na frente mantém a
ordem de criação (bom para índices); a parte aleatória impede adivinhar o próximo id, o que ajuda
contra BOLA por tentativa (OWASP API1).
"""

import os
import time
import uuid

_MASCARA_48 = (1 << 48) - 1
_MASCARA_62 = (1 << 62) - 1


def uuid7() -> uuid.UUID:
    milissegundos = time.time_ns() // 1_000_000
    aleatorio = int.from_bytes(os.urandom(10), "big")  # 80 bits; usamos 74
    rand_a = (aleatorio >> 62) & 0xFFF
    rand_b = aleatorio & _MASCARA_62
    valor = (
        (milissegundos & _MASCARA_48) << 80
        | 0x7 << 76  # versão
        | rand_a << 64
        | 0b10 << 62  # variante RFC 9562
        | rand_b
    )
    return uuid.UUID(int=valor)


def timestamp_ms(identificador: uuid.UUID) -> int:
    """Milissegundos Unix gravados num UUIDv7."""
    return identificador.int >> 80
