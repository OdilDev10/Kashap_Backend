"""OCR service for voucher image processing using PaddleOCR."""

import asyncio
import logging
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

try:
    from paddleocr import PaddleOCR
except Exception as exc:  # pragma: no cover - import error path depends on host env
    PaddleOCR = Any  # type: ignore[misc,assignment]
    _paddle_import_error = exc
else:
    _paddle_import_error = None

from app.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

# Global OCR engine (initialized in lifespan)
ocr_engine: Optional[PaddleOCR] = None
ocr_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr_worker")


def initialize_ocr():
    """Initialize PaddleOCR engine (called in app lifespan)."""
    global ocr_engine
    if PaddleOCR is Any:
        raise RuntimeError(
            "OCR is required but PaddleOCR dependencies are not available. "
            f"Import error: {_paddle_import_error}"
        )

    logger.info("Initializing PaddleOCR engine...")
    ocr_engine = PaddleOCR(
        use_angle_cls=settings.ocr_use_angle_cls,
        lang=settings.ocr_lang,
    )
    logger.info("PaddleOCR initialized successfully")


def _extract_amount_dominican(text: str) -> Optional[Decimal]:
    """
    Extract monetary amount from Dominican voucher text.
    Looks for patterns like: $1,000.00, RD$ 1,000.00, US$ 250.00, etc.
    """
    # Normalize text to handle common OCR artifacts in numbers
    # Sometimes OCR puts spaces in numbers: 1 000.00 -> 1000.00
    clean_text = re.sub(r"(\d)\s+(\d{3})", r"\1\2", text)
    
    # Priority 1: Patterns with currency symbols and optional decimals
    priority_patterns = [
        r"(?:RD|US)\s*\$?\s*([\d,]+(?:\.\d{2})?)", # RD$ 1,000.00 or RD$ 1,000
        r"\$\s*([\d,]+(?:\.\d{2})?)",             # $ 1,000.00 or $ 1,000
    ]
    
    # Priority 2: Numbers with decimals but no currency symbol
    decimal_patterns = [
        r"(?:\s|^)([\d,]+\.\d{2})(?:\s|$)",  # 1,000.00
    ]

    # Try priority patterns first
    for patterns in [priority_patterns, decimal_patterns]:
        found_amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
            for match in matches:
                try:
                    clean = match.replace(",", "")
                    amount = Decimal(clean)
                    if 0.01 <= amount <= 10000000:
                        found_amounts.append(amount)
                except:
                    continue
        if found_amounts:
            # Usually the largest amount with a currency symbol is the transaction amount
            return max(found_amounts)
    
    return None


def _extract_date_dominican(text: str) -> Optional[datetime]:
    """
    Extract date from Dominican voucher text.
    Supports: DD/MM/YYYY, DD-MM-YYYY, DD mes YYYY, etc.
    """
    # Numeric patterns: DD/MM/YYYY or YYYY/MM/DD
    numeric_patterns = [
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
        r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
    ]

    for pattern in numeric_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match[0]) == 4: # YYYY/MM/DD
                    year, month, day = int(match[0]), int(match[1]), int(match[2])
                else: # DD/MM/YYYY
                    day, month, year = int(match[0]), int(match[1]), int(match[2])
                
                if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2100:
                    return datetime(year, month, day)
            except ValueError:
                continue

    # Text-based months (Popular style: 2 mar 2026)
    months_map = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
        'jan': 1, 'apr': 4, 'aug': 8, 'dec': 12 # English fallbacks
    }
    
    months_pattern = "|".join(months_map.keys())
    text_date_pattern = rf"(\d{{1,2}})\s+({months_pattern})[a-z]*\s+(\d{{4}})"
    
    matches = re.findall(text_date_pattern, text, re.IGNORECASE)
    if matches:
        for day_str, month_str, year_str in matches:
            try:
                day = int(day_str)
                month = months_map[month_str.lower()[:3]]
                year = int(year_str)
                return datetime(year, month, day)
            except (ValueError, KeyError):
                continue

    return None


def _extract_bank_reference(text: str) -> Optional[str]:
    """Extract bank transaction reference or authorization code."""
    # Common Dominican bank reference patterns including "No. Referencia" and "No. Confirmación"
    keywords = (
        r"ref|referencia|reference|autorizaci[óo]n|authorization|code|"
        r"confirmaci[óo]n|aprobaci[óo]n|comprobante|n[úu]mero"
    )
    patterns = [
        rf"(?:{keywords})(?:\s+|[.\s]+|[:\s]+)(?:ref(?:erencia)?\s+)?((?=[A-Z0-9\-]{{6,25}}\b)(?=[A-Z0-9\-]*\d)[A-Z0-9\-]+)",
        r"#\s*([A-Z0-9\-]{6,20})",
        # Pattern for BHD style: M11-1773-7951-5758-5
        r"([A-Z]\d{2}-\d{4}-\d{4}-\d{4}-\d)"
    ]

    for idx, pattern in enumerate(patterns):
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Clean up the reference (remove trailing dots or spaces)
            ref = matches[0].strip().strip('.')
            # For the broad keyword pattern require at least one digit to avoid
            # capturing label words like "referencia" as the value.
            needs_digit = idx == 0
            if len(ref) >= 6 and (any(ch.isdigit() for ch in ref) or not needs_digit):
                return ref

    return None


def _extract_bank_name(text: str) -> Optional[str]:
    """Detect the bank name based on keywords in text."""
    banks = {
        "Popular": ["popular", "bpd"],
        "BHD": ["bhd", "leon"],
        "BDI": ["bdi"],
        "Banreservas": ["reservas", "banreservas"],
        "Scotiabank": ["scotia"],
        "Progreso": ["progreso"],
        "Santa Cruz": ["santa cruz"],
        "Promerica": ["promerica"],
        "Ademi": ["ademi"],
        "JMMB": ["jmmb"],
    }

    text_lower = text.lower()
    for bank_name, keywords in banks.items():
        if any(keyword in text_lower for keyword in keywords):
            return bank_name
    
    return None


def _process_ocr_result(image_path: str) -> dict:
    """Process image through PaddleOCR (runs in ThreadPoolExecutor)."""
    global ocr_engine

    if ocr_engine is None:
        raise AppException("OCR engine not initialized", code="OCR_NOT_READY")

    try:
        # Run OCR
        result = ocr_engine.ocr(image_path, cls=True)

        # Extract text from OCR result
        extracted_text = ""
        confidence_scores = []

        if result:
            for line in result:
                if line:
                    for word_info in line:
                        text = word_info[1][0] # PaddleOCR format: [text, confidence]
                        confidence = word_info[1][1]
                        extracted_text += text + " "
                        confidence_scores.append(confidence)

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

        return {
            "raw_text": extracted_text.strip(),
            "confidence": float(avg_confidence),
            "raw_result": result,
        }
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        raise AppException(f"OCR processing failed: {str(e)}", code="OCR_PROCESS_ERROR")


async def process_voucher_image(image_path: str) -> dict:
    """
    Process voucher image asynchronously using PaddleOCR in ThreadPoolExecutor.
    Returns extracted payment data.
    """
    loop = asyncio.get_event_loop()

    try:
        # Run OCR in thread pool to avoid blocking
        ocr_result = await loop.run_in_executor(ocr_executor, _process_ocr_result, image_path)

        raw_text = ocr_result["raw_text"]
        confidence = ocr_result["confidence"]

        # Extract payment data
        amount = _extract_amount_dominican(raw_text)
        transaction_date = _extract_date_dominican(raw_text)
        bank_reference = _extract_bank_reference(raw_text)
        bank_name = _extract_bank_name(raw_text)

        # Detect currency
        currency = "DOP"
        if "US$" in raw_text.upper() or "USD" in raw_text.upper():
            currency = "USD"

        extraction_status = "success" if amount and transaction_date else "partial"
        if not amount and not transaction_date:
            extraction_status = "failed"

        return {
            "status": extraction_status,
            "raw_text": raw_text,
            "confidence": confidence,
            "extracted_data": {
                "amount": float(amount) if amount else None,
                "currency": currency,
                "transaction_date": transaction_date.isoformat() if transaction_date else None,
                "bank_reference": bank_reference,
                "bank_name": bank_name,
            },
            "processed_at": datetime.now().isoformat(),
        }
    except AppException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in voucher processing")
        raise AppException(f"Voucher processing failed: {str(e)}", code="VOUCHER_PROCESS_ERROR")


def close_ocr():
    """Clean up OCR resources (called in app shutdown)."""
    global ocr_engine
    if ocr_executor:
        ocr_executor.shutdown(wait=True)
    logger.info("OCR engine shut down")


class OCRService:
    """Backward-compatible wrapper around the current OCR helpers."""

    async def extract_from_image(self, file_content: bytes) -> dict:
        """Process an uploaded image buffer and normalize the OCR payload."""
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name

            result = await process_voucher_image(temp_path)
            extracted = result.get("extracted_data", {})

            return {
                "extracted_text": result.get("raw_text"),
                "detected_amount": extracted.get("amount"),
                "detected_currency": extracted.get("currency"),
                "detected_date": extracted.get("transaction_date"),
                "detected_reference": extracted.get("bank_reference"),
                "detected_bank_name": extracted.get("bank_name"),
                "confidence_score": result.get("confidence", 0.0),
                "appears_to_be_receipt": bool(result.get("raw_text")),
                "validation_summary": result.get("status"),
                "status": result.get("status"),
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
