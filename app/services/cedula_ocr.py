"""OCR extraction functions for Dominican ID cards (Cédula)."""

import re
from datetime import datetime
from typing import Optional


def _normalize_text(text: str) -> str:
    """Normalize OCR text by removing extra spaces and common artifacts."""
    text = re.sub(r"\s+", " ", text)
    text = text.upper()
    return text.strip()


def _extract_cedula_number(text: str) -> Optional[str]:
    """
    Extract Cédula number from OCR text.
    Dominican Cédula format: 000-0000000-0 (11 digits with hyphens)
    """
    patterns = [
        r"\b(\d{3}[-\s]?\d{7}[-\s]?\d)\b",
        r"\b(\d{11})\b",
        r"C[DÉ]DULA[:\s]*(\d{3}[-\s]?\d{7}[-\s]?\d)",
        r"No\.\s*(\d{3}[-\s]?\d{7}[-\s]?\d)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            cedula = match.group(1)
            cedula = re.sub(r"[-\s]", "", cedula)
            if len(cedula) == 11 and cedula.isdigit():
                formatted = f"{cedula[:3]}-{cedula[3:10]}-{cedula[10]}"
                return formatted
    return None


def _extract_name(text: str) -> Optional[str]:
    """
    Extract name from Cédula OCR text.
    Dominican IDs typically have NAME in uppercase.
    """
    patterns = [
        r"NOMBRE[S]?[:\s]+([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|APELLIDO|PROCEDENCIA|FECHA|NAC|SEXO)",
        r"NOMBRE[S]?\s*(PRIMER\s+)?([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|APELLIDO)",
        r"^([A-ZÁÉÍÓÚÑ]{2,}\s+[A-ZÁÉÍÓÚÑ\s]+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            name = match.group(1).strip() if match.group(1) else match.group(2).strip()
            name = re.sub(r"\s+", " ", name)
            if len(name) >= 3:
                return name
    return None


def _extract_last_name(text: str) -> Optional[str]:
    """Extract last name from Cédula OCR text."""
    patterns = [
        r"APELLIDO[S]?[:\s]+([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|NACIMIENTO|SEXO|FECHA)",
        r"APELLIDO\s*(SEGUNDO\s+)?([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|NACIMIENTO|SEXO)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            lastname = (
                match.group(2).strip() if match.group(2) else match.group(1).strip()
            )
            lastname = re.sub(r"\s+", " ", lastname)
            if len(lastname) >= 3:
                return lastname
    return None


def _extract_birth_date(text: str) -> Optional[str]:
    """
    Extract birth date from Cédula OCR text.
    Supports: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
    """
    patterns = [
        r"FECHA\s+DE\s+NACIMIENTO[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"NAC(?:IMIENTO)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
    ]

    months_map = {
        "ene": 1,
        "ene.": 1,
        "jan": 1,
        "feb": 2,
        "feb.": 2,
        "mar": 3,
        "mar.": 3,
        "abr": 4,
        "abr.": 4,
        "apr": 4,
        "may": 5,
        "may.": 5,
        "jun": 6,
        "jun.": 6,
        "jul": 7,
        "jul.": 7,
        "ago": 8,
        "ago.": 8,
        "aug": 8,
        "sep": 9,
        "sep.": 9,
        "sept": 9,
        "sept.": 9,
        "oct": 10,
        "oct.": 10,
        "nov": 11,
        "nov.": 11,
        "dic": 12,
        "dic.": 12,
        "dec": 12,
        "dec.": 12,
    }

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            for month_name, month_num in months_map.items():
                if month_name.lower() in date_str.lower():
                    date_pattern = rf"(\d{1, 2})[/-]({month_name})[/-]?(\d{{2,4}})"
                    date_match = re.search(date_pattern, date_str, re.IGNORECASE)
                    if date_match:
                        day, month, year = (
                            int(date_match.group(1)),
                            month_num,
                            int(date_match.group(3)),
                        )
                        if year < 100:
                            year += 2000 if year < 50 else 1900
                        try:
                            dt = datetime(year, month, day)
                            return dt.strftime("%Y-%m-%d")
                        except ValueError:
                            continue
            try:
                parts = re.split(r"[/-]", date_str)
                if len(parts) == 3:
                    if len(parts[2]) == 2:
                        parts[2] = (
                            "20" + parts[2] if int(parts[2]) < 50 else "19" + parts[2]
                        )
                    dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def _extract_nationality(text: str) -> Optional[str]:
    """Extract nationality from Cédula OCR text."""
    patterns = [
        r"NACIONALIDAD[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|SEXO|ESTADO)",
        r"PAÍS\s+DE\s+NACIMIENTO[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|SEXO|ESTADO)",
    ]

    nationality_keywords = [
        "DOMINICANA",
        "HAITIAN",
        "AMERICANA",
        "VENEZUELA",
        "COLOMBIA",
        "ESPAÑA",
        "CHINA",
        "INDIA",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            nationality = match.group(1).strip()
            for kw in nationality_keywords:
                if kw in nationality.upper():
                    return kw.capitalize()
            return nationality

    if "REPUBLICA DOMINICANA" in text.upper():
        return "Dominicana"
    return None


def _extract_gender(text: str) -> Optional[str]:
    """Extract gender from Cédula OCR text."""
    patterns = [
        r"SEXO[:\s]*([MF]\.?\s*[A-Z]*|MASCULINO|FEMENINO)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            gender = match.group(1).upper().strip()
            if gender.startswith("M"):
                return "M"
            elif gender.startswith("F"):
                return "F"
    return None


def _extract_expiration_date(text: str) -> Optional[str]:
    """Extract expiration/validity date from Cédula OCR text."""
    patterns = [
        r"FECHA\s+DE\s+VENCIMIENTO[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"VÁLIDO\s+HASTA[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"EXPIR[ÁA][\s:]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            try:
                parts = re.split(r"[/-]", date_str)
                if len(parts) == 3:
                    if len(parts[2]) == 2:
                        parts[2] = (
                            "20" + parts[2] if int(parts[2]) < 50 else "19" + parts[2]
                        )
                    dt = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def _extract_blood_type(text: str) -> Optional[str]:
    """Extract blood type from Cédula OCR text."""
    patterns = [
        r"TIPO\s+DE\s+SANGRE[:\s]*([A-Z][+-]?|O[+-]?|AB[+-]?)",
        r"SANGRE[:\s]*([A-Z][+-]?|O[+-]?|AB[+-]?)",
        r"GRUPO\s+SANGUÍNEO[:\s]*([A-Z][+-]?)",
    ]

    blood_types = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            blood = match.group(1).upper().strip()
            for bt in blood_types:
                if bt.replace("+", "").replace("-", "") in blood.upper():
                    if "+" in blood or "-" in blood:
                        return bt
                    if blood in ["A", "B", "AB", "O"]:
                        return bt[0] + "+"
    return None


def _extract_civil_status(text: str) -> Optional[str]:
    """Extract civil status from Cédula OCR text."""
    patterns = [
        r"ESTADO\s+CIVIL[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|DIRECCI|OCUPACI)",
        r"CIVIL[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|DIRECCI|OCUPACI)",
    ]

    status_map = {
        "SOLTERO": "Soltero",
        "SOLTERA": "Soltero",
        "CASADO": "Casado",
        "CASADA": "Casado",
        "UNIÓN LIBRE": "Unión Libre",
        "CONCUBINATO": "Unión Libre",
        "DIVORCIADO": "Divorciado",
        "DIVORCIADA": "Divorciado",
        "VIUDO": "Viudo",
        "VIUDA": "Viudo",
    }

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            status = match.group(1).strip().upper()
            for key, value in status_map.items():
                if key in status:
                    return value
    return None


def _extract_address(text: str) -> Optional[str]:
    """Extract address from Cédula OCR text."""
    patterns = [
        r"DIRECCIÓN[:\s]*([A-Z0-9ÁÉÍÓÚÑ\s,.#-]+?)(?=\n|MUNICIPI|SECTOR|PROVINCIA)",
        r"ADDRESS[:\s]*([A-Z0-9ÁÉÍÓÚÑ\s,.#-]+?)(?=\n|MUNICIPI|SECTOR|PROVINCIA)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            address = match.group(1).strip()
            address = re.sub(r"\s+", " ", address)
            if len(address) >= 10:
                return address
    return None


def _extract_municipality(text: str) -> Optional[str]:
    """Extract municipality from Cédula OCR text."""
    patterns = [
        r"MUNICIPIO[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|SECTOR|PROVINCIA|DISTRITO)",
        r"MUNICIPI[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?=\n|SECTOR|PROVINCIA|DISTRITO)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            municipality = match.group(1).strip()
            municipality = re.sub(r"\s+", " ", municipality)
            if len(municipality) >= 2:
                return municipality
    return None


def extract_cedula_data(raw_text: str) -> dict:
    """
    Extract all relevant data from Dominican Cédula OCR text.
    Returns a dictionary with extracted fields.
    """
    text = _normalize_text(raw_text)

    cedula_number = _extract_cedula_number(text)
    name = _extract_name(text)
    last_name = _extract_last_name(text)
    birth_date = _extract_birth_date(text)
    nationality = _extract_nationality(text)
    gender = _extract_gender(text)
    expiration_date = _extract_expiration_date(text)
    blood_type = _extract_blood_type(text)
    civil_status = _extract_civil_status(text)
    address = _extract_address(text)
    municipality = _extract_municipality(text)

    extracted_count = sum(
        1
        for x in [
            cedula_number,
            name,
            last_name,
            birth_date,
            nationality,
            gender,
            expiration_date,
            blood_type,
            civil_status,
            address,
            municipality,
        ]
        if x is not None
    )

    extraction_score = extracted_count / 11

    return {
        "extracted_text": raw_text,
        "detected_cedula_number": cedula_number,
        "detected_name": name,
        "detected_last_name": last_name,
        "detected_birth_date": birth_date,
        "detected_nationality": nationality,
        "detected_gender": gender,
        "detected_expiration_date": expiration_date,
        "detected_blood_type": blood_type,
        "detected_civil_status": civil_status,
        "detected_address": address,
        "detected_municipality": municipality,
        "extraction_score": extraction_score,
        "fields_extracted": extracted_count,
        "missing_fields": 11 - extracted_count,
    }


def compare_cedula_with_customer(ocr_data: dict, customer_data: dict) -> dict:
    """
    Compare OCR extracted data with customer registration data.
    Returns a comparison report.
    """
    comparison = {
        "matches": [],
        "mismatches": [],
        "unverified": [],
        "overall_match": True,
        "confidence_score": 0.0,
    }

    customer_cedula = (
        customer_data.get("document_number", "").replace("-", "").replace(" ", "")
    )
    ocr_cedula = (
        (ocr_data.get("detected_cedula_number") or "").replace("-", "").replace(" ", "")
    )

    if ocr_cedula and customer_cedula:
        if ocr_cedula == customer_cedula:
            comparison["matches"].append(("cedula", ocr_cedula))
        else:
            comparison["mismatches"].append(("cedula", ocr_cedula, customer_cedula))
            comparison["overall_match"] = False
    else:
        comparison["unverified"].append("cedula")

    customer_name = (customer_data.get("first_name", "") or "").upper()
    customer_lastname = (customer_data.get("last_name", "") or "").upper()
    ocr_name = (ocr_data.get("detected_name", "") or "").upper()
    ocr_lastname = (ocr_data.get("detected_last_name", "") or "").upper()

    name_match = False
    if ocr_name and customer_name:
        customer_first = customer_name.split()[0] if customer_name.split() else ""
        if customer_first and customer_first in ocr_name:
            comparison["matches"].append(("name", ocr_name))
            name_match = True
        elif not customer_first:
            comparison["unverified"].append("name")
        else:
            comparison["mismatches"].append(("name", ocr_name, customer_name))
            comparison["overall_match"] = False

    if ocr_lastname and customer_lastname:
        customer_last = (
            customer_lastname.split()[-1] if customer_lastname.split() else ""
        )
        if customer_last and customer_last in ocr_lastname:
            comparison["matches"].append(("last_name", ocr_lastname))
        elif not customer_last:
            comparison["unverified"].append("last_name")
        else:
            comparison["mismatches"].append(
                ("last_name", ocr_lastname, customer_lastname)
            )
            comparison["overall_match"] = False

    total_checks = len(comparison["matches"]) + len(comparison["mismatches"])
    if total_checks > 0:
        comparison["confidence_score"] = len(comparison["matches"]) / total_checks

    return comparison
