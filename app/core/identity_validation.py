"""Identity and contact normalization/validation helpers."""

from __future__ import annotations

import re

from app.core.exceptions import ValidationException


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValidationException("Número de teléfono inválido")
    return digits


def normalize_cedula(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 11:
        raise ValidationException("La cédula debe tener 11 dígitos")
    if len(set(digits)) == 1:
        raise ValidationException("Cédula inválida")
    if not _is_valid_cedula_checksum(digits):
        raise ValidationException("Cédula inválida")
    return digits


def normalize_rnc(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 9:
        raise ValidationException("El RNC debe tener 9 dígitos")
    if len(set(digits)) == 1:
        raise ValidationException("RNC inválido")
    if not _is_valid_rnc_checksum(digits):
        raise ValidationException("RNC inválido")
    return digits


def _is_valid_cedula_checksum(digits: str) -> bool:
    weights = (1, 2) * 5
    total = 0
    for idx in range(10):
        product = int(digits[idx]) * weights[idx]
        if product >= 10:
            product = (product // 10) + (product % 10)
        total += product
    verifier = (10 - (total % 10)) % 10
    return verifier == int(digits[10])


def _is_valid_rnc_checksum(digits: str) -> bool:
    weights = [7, 9, 8, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights[i] for i in range(8))
    residue = total % 11
    verifier = 0
    if residue == 0:
        verifier = 2
    elif residue == 1:
        verifier = 1
    else:
        verifier = 11 - residue
    return verifier == int(digits[8])
