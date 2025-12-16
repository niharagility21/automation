"""
PDF parsing and appraisal value extraction.

This module extracts text from PDF documents (auction appraisals) and
uses regex patterns to find estimated values and property details.
Falls back to OCR if direct text extraction fails.
"""

import re
import os
from pathlib import Path
from typing import Dict, Optional, List
import PyPDF2

from config.settings import TESSERACT_CMD, PDF_DOWNLOAD_DIR
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Try to import OCR dependencies (optional)
try:
    import pytesseract
    from PIL import Image
    import pdf2image

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning(
        "OCR dependencies not available (pytesseract, PIL, pdf2image). "
        "PDF parsing will use text extraction only."
    )


class PDFParser:
    """
    Extracts appraisal values and property details from PDF documents.

    Attributes:
        pdf_path: Path to PDF file
        text_content: Extracted text content
    """

    # Regex patterns for common appraisal fields
    VALUE_PATTERNS = [
        r"estimated?\s*value[:\s]*\$?([\d,]+\.?\d*)",
        r"appraised?\s*value[:\s]*\$?([\d,]+\.?\d*)",
        r"market\s*value[:\s]*\$?([\d,]+\.?\d*)",
        r"fair\s*market\s*value[:\s]*\$?([\d,]+\.?\d*)",
        r"valuation[:\s]*\$?([\d,]+\.?\d*)",
        r"value[:\s]*\$?([\d,]+\.?\d*)",
    ]

    ADDRESS_PATTERNS = [
        r"property\s*address[:\s]*([^\n]+)",
        r"subject\s*property[:\s]*([^\n]+)",
        r"location[:\s]*([^\n]+)",
    ]

    BED_BATH_PATTERNS = [
        r"(\d+)\s*bed(?:room)?s?",
        r"(\d+\.?\d*)\s*bath(?:room)?s?",
    ]

    SQFT_PATTERNS = [
        r"([\d,]+)\s*sq\.?\s*ft",
        r"([\d,]+)\s*square\s*feet",
        r"gross\s*living\s*area[:\s]*([\d,]+)",
    ]

    def __init__(self, pdf_path: Path):
        """
        Initialize PDF parser.

        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = Path(pdf_path)
        self.text_content: Optional[str] = None

    async def extract_text(self) -> str:
        """
        Extract text from PDF using PyPDF2.

        Returns:
            Extracted text content

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If PDF reading fails
        """
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_parts = []

                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num}: {e}")

                self.text_content = "\n".join(text_parts)
                logger.debug(f"Extracted {len(self.text_content)} characters from {self.pdf_path.name}")

                return self.text_content

        except Exception as e:
            logger.error(f"Failed to read PDF {self.pdf_path}: {e}")
            # Try OCR as fallback
            if OCR_AVAILABLE:
                return await self._extract_text_ocr()
            raise

    async def _extract_text_ocr(self) -> str:
        """
        Extract text using OCR (fallback method).

        Returns:
            OCR-extracted text

        Raises:
            Exception: If OCR fails
        """
        if not OCR_AVAILABLE:
            raise RuntimeError("OCR dependencies not available")

        try:
            logger.info(f"Attempting OCR extraction for {self.pdf_path.name}")

            # Convert PDF to images
            images = pdf2image.convert_from_path(str(self.pdf_path))
            text_parts = []

            for i, image in enumerate(images):
                try:
                    text = pytesseract.image_to_string(image)
                    text_parts.append(text)
                except Exception as e:
                    logger.warning(f"OCR failed for page {i}: {e}")

            self.text_content = "\n".join(text_parts)
            logger.debug(f"OCR extracted {len(self.text_content)} characters")

            return self.text_content

        except Exception as e:
            logger.error(f"OCR extraction failed for {self.pdf_path}: {e}")
            raise

    def _extract_with_patterns(
        self,
        patterns: List[str],
        flags: int = re.IGNORECASE
    ) -> Optional[str]:
        """
        Extract value using regex patterns.

        Args:
            patterns: List of regex patterns to try
            flags: Regex flags (default: case-insensitive)

        Returns:
            First matched value or None
        """
        if not self.text_content:
            return None

        for pattern in patterns:
            match = re.search(pattern, self.text_content, flags)
            if match:
                return match.group(1).strip()

        return None

    def extract_estimated_value(self) -> Optional[float]:
        """
        Extract estimated property value from PDF.

        Returns:
            Estimated value as float or None if not found

        Example:
            >>> parser = PDFParser(Path("appraisal.pdf"))
            >>> await parser.extract_text()
            >>> value = parser.extract_estimated_value()
            >>> # 450000.0
        """
        value_str = self._extract_with_patterns(self.VALUE_PATTERNS)

        if value_str:
            # Clean and convert to float
            cleaned = value_str.replace(',', '').replace('$', '').strip()
            try:
                return float(cleaned)
            except ValueError:
                logger.warning(f"Could not convert value to float: {value_str}")

        return None

    def extract_property_details(self) -> Dict[str, any]:
        """
        Extract comprehensive property details from PDF.

        Returns:
            Dict with address, bedrooms, bathrooms, sqft, etc.

        Example:
            >>> parser = PDFParser(Path("appraisal.pdf"))
            >>> await parser.extract_text()
            >>> details = parser.extract_property_details()
            >>> # {"address": "123 Main St", "bedrooms": 3, ...}
        """
        details = {}

        # Extract address
        address = self._extract_with_patterns(self.ADDRESS_PATTERNS)
        if address:
            details["address"] = address

        # Extract bedrooms/bathrooms
        bed_match = re.search(self.BED_BATH_PATTERNS[0], self.text_content or "", re.IGNORECASE)
        if bed_match:
            details["bedrooms"] = int(bed_match.group(1))

        bath_match = re.search(self.BED_BATH_PATTERNS[1], self.text_content or "", re.IGNORECASE)
        if bath_match:
            details["bathrooms"] = float(bath_match.group(1))

        # Extract square footage
        sqft_str = self._extract_with_patterns(self.SQFT_PATTERNS)
        if sqft_str:
            try:
                details["sqft"] = int(sqft_str.replace(',', ''))
            except ValueError:
                logger.warning(f"Could not convert sqft to int: {sqft_str}")

        return details

    def calculate_confidence_score(self) -> float:
        """
        Calculate confidence score for extraction (0.0 to 1.0).

        Based on:
        - Text length (longer = more confident)
        - Number of fields extracted
        - Presence of key terms

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not self.text_content:
            return 0.0

        score = 0.0

        # Text length factor (max 0.3)
        text_length = len(self.text_content)
        if text_length > 500:
            score += 0.3
        elif text_length > 200:
            score += 0.2
        elif text_length > 100:
            score += 0.1

        # Value found (0.4)
        if self.extract_estimated_value():
            score += 0.4

        # Property details found (0.3)
        details = self.extract_property_details()
        score += 0.1 * min(len(details), 3) / 3

        return min(score, 1.0)

    async def extract_appraisal_values(self) -> Dict[str, any]:
        """
        Extract all appraisal data from PDF (main method).

        Returns:
            Dict with estimated_value, property_details, confidence_score

        Example:
            >>> parser = PDFParser(Path("appraisal.pdf"))
            >>> data = await parser.extract_appraisal_values()
            >>> print(data)
            {
                "estimated_value": 450000.0,
                "property_details": {"address": "123 Main St", "bedrooms": 3},
                "confidence_score": 0.8,
                "source": "pdf"
            }
        """
        try:
            # Extract text
            await self.extract_text()

            # Extract all data
            result = {
                "estimated_value": self.extract_estimated_value(),
                "property_details": self.extract_property_details(),
                "confidence_score": self.calculate_confidence_score(),
                "source": "pdf",
                "pdf_path": str(self.pdf_path),
            }

            logger.info(
                f"PDF extraction complete for {self.pdf_path.name}: "
                f"value={result['estimated_value']}, confidence={result['confidence_score']:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to extract appraisal values from {self.pdf_path}: {e}")
            return {
                "estimated_value": None,
                "property_details": {},
                "confidence_score": 0.0,
                "source": "pdf",
                "error": str(e),
            }


async def extract_appraisal_values(pdf_path: Path) -> Dict[str, any]:
    """
    Convenience function to extract appraisal values from a PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dict with extracted appraisal data

    Example:
        >>> from utils.pdf_parser import extract_appraisal_values
        >>> data = await extract_appraisal_values(Path("appraisal.pdf"))
    """
    parser = PDFParser(pdf_path)
    return await parser.extract_appraisal_values()
