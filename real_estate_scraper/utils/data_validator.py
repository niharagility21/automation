"""
Data validation and cleaning utilities.

This module validates scraped data against Pydantic models and provides
cleaning functions for common data types (prices, addresses, etc.).
"""

import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger(__name__)


class DataValidator:
    """
    Validates and cleans scraped property data.

    Provides methods for:
    - Cleaning prices (remove $, commas, convert to float)
    - Validating addresses
    - Cleaning and validating numeric fields
    - Handling missing data with defaults
    """

    @staticmethod
    def clean_price(price_str: Optional[str]) -> Optional[float]:
        """
        Clean and convert price string to float.
        Supports both USD ($) and Indian Rupees (₹) formats.

        Args:
            price_str: Raw price string (e.g., "$450,000", "1.2M", "₹1.2 Cr", "₹45 Lac")

        Returns:
            Price as float or None if invalid

        Example:
            >>> DataValidator.clean_price("$450,000")
            450000.0
            >>> DataValidator.clean_price("1.2M")
            1200000.0
            >>> DataValidator.clean_price("₹1.2 Cr")
            12000000.0
            >>> DataValidator.clean_price("₹45 Lac")
            4500000.0
            >>> DataValidator.clean_price("₹1.5 L")
            150000.0
            >>> DataValidator.clean_price("invalid")
            None
        """
        if not price_str:
            return None

        try:
            # Remove whitespace
            cleaned = str(price_str).strip()

            # Handle Indian Rupee formats (Crores and Lakhs)
            # 1 Crore = 10,000,000 (1,00,00,000)
            # 1 Lakh = 100,000 (1,00,000)
            multiplier = 1

            # Check for Crore/Cr
            if re.search(r'(?:Cr|Crore)', cleaned, re.IGNORECASE):
                multiplier = 10000000  # 1 Crore
                cleaned = re.sub(r'(?:Cr|Crore)', '', cleaned, flags=re.IGNORECASE)

            # Check for Lakh/Lac/L (but not "L" if followed by other letters)
            elif re.search(r'(?:Lakh|Lac)\b', cleaned, re.IGNORECASE):
                multiplier = 100000  # 1 Lakh
                cleaned = re.sub(r'(?:Lakh|Lac)', '', cleaned, flags=re.IGNORECASE)

            # Check for standalone L (Lakh abbreviation)
            elif re.search(r'\bL\b', cleaned):
                multiplier = 100000  # 1 Lakh
                cleaned = re.sub(r'\bL\b', '', cleaned)

            # Check for K (thousand) - both USD and INR
            elif re.search(r'\bK\b', cleaned, re.IGNORECASE):
                multiplier = 1000
                cleaned = re.sub(r'\bK\b', '', cleaned, flags=re.IGNORECASE)

            # Check for M (million) - USD format
            elif re.search(r'\bM\b', cleaned, re.IGNORECASE):
                multiplier = 1000000
                cleaned = re.sub(r'\bM\b', '', cleaned, flags=re.IGNORECASE)

            # Remove currency symbols (₹ and $) and commas
            cleaned = cleaned.replace('₹', '').replace('$', '').replace(',', '').strip()

            # Extract numeric value (handles decimals)
            match = re.search(r'([\d.]+)', cleaned)
            if match:
                value = float(match.group(1)) * multiplier
                return value

            return None

        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to clean price '{price_str}': {e}")
            return None

    @staticmethod
    def clean_numeric(value_str: Optional[str]) -> Optional[int]:
        """
        Clean and convert numeric string to int.

        Args:
            value_str: Raw numeric string (e.g., "3 bedrooms", "2,500 sqft")

        Returns:
            Integer value or None if invalid

        Example:
            >>> DataValidator.clean_numeric("3 bedrooms")
            3
            >>> DataValidator.clean_numeric("2,500")
            2500
        """
        if not value_str:
            return None

        try:
            cleaned = str(value_str).replace(',', '').strip()
            match = re.search(r'(\d+)', cleaned)
            if match:
                return int(match.group(1))
            return None

        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to clean numeric '{value_str}': {e}")
            return None

    @staticmethod
    def clean_float(value_str: Optional[str]) -> Optional[float]:
        """
        Clean and convert string to float.

        Args:
            value_str: Raw string (e.g., "2.5 baths")

        Returns:
            Float value or None if invalid
        """
        if not value_str:
            return None

        try:
            cleaned = str(value_str).replace(',', '').strip()
            match = re.search(r'([\d.]+)', cleaned)
            if match:
                return float(match.group(1))
            return None

        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to clean float '{value_str}': {e}")
            return None

    @staticmethod
    def clean_address(address_str: Optional[str]) -> Optional[str]:
        """
        Clean and validate address string.

        Args:
            address_str: Raw address string

        Returns:
            Cleaned address or None if invalid

        Example:
            >>> DataValidator.clean_address("  123 Main St, NYC, NY  ")
            '123 Main St, NYC, NY'
        """
        if not address_str:
            return None

        # Remove extra whitespace
        cleaned = ' '.join(str(address_str).split())

        # Basic validation: should have at least street number and name
        if len(cleaned) < 5:
            logger.debug(f"Address too short: '{cleaned}'")
            return None

        # Should contain at least one digit (street number)
        if not re.search(r'\d', cleaned):
            logger.debug(f"Address missing street number: '{cleaned}'")
            return None

        return cleaned

    @staticmethod
    def validate_geolocation(lat: Optional[float], lng: Optional[float]) -> bool:
        """
        Validate latitude and longitude values.

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            True if valid, False otherwise
        """
        if lat is None or lng is None:
            return False

        # Check valid ranges
        if not (-90 <= lat <= 90):
            logger.debug(f"Invalid latitude: {lat}")
            return False

        if not (-180 <= lng <= 180):
            logger.debug(f"Invalid longitude: {lng}")
            return False

        return True

    @staticmethod
    def clean_date(date_str: Optional[str]) -> Optional[str]:
        """
        Clean and standardize date string.

        Args:
            date_str: Raw date string

        Returns:
            ISO format date string (YYYY-MM-DD) or None

        Example:
            >>> DataValidator.clean_date("12/25/2024")
            '2024-12-25'
        """
        if not date_str:
            return None

        # Common date formats to try
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]

        for fmt in formats:
            try:
                date_obj = datetime.strptime(str(date_str).strip(), fmt)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue

        logger.debug(f"Could not parse date: '{date_str}'")
        return None

    @staticmethod
    def validate_required_fields(
        data: Dict[str, Any],
        required_fields: List[str]
    ) -> tuple[bool, List[str]]:
        """
        Validate that required fields are present and non-empty.

        Args:
            data: Data dict to validate
            required_fields: List of required field names

        Returns:
            Tuple of (is_valid, missing_fields)

        Example:
            >>> data = {"address": "123 Main St", "price": 450000}
            >>> is_valid, missing = DataValidator.validate_required_fields(
            ...     data, ["address", "price", "bedrooms"]
            ... )
            >>> is_valid
            False
            >>> missing
            ['bedrooms']
        """
        missing = []

        for field in required_fields:
            value = data.get(field)
            if value is None or value == "" or value == []:
                missing.append(field)

        is_valid = len(missing) == 0
        return is_valid, missing

    @staticmethod
    def apply_defaults(data: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values to missing fields.

        Args:
            data: Data dict
            defaults: Dict of field -> default_value

        Returns:
            Data dict with defaults applied

        Example:
            >>> data = {"address": "123 Main St"}
            >>> defaults = {"price": None, "bedrooms": 0}
            >>> result = DataValidator.apply_defaults(data, defaults)
            >>> result
            {'address': '123 Main St', 'price': None, 'bedrooms': 0}
        """
        result = data.copy()

        for field, default_value in defaults.items():
            if field not in result or result[field] is None:
                result[field] = default_value

        return result

    @staticmethod
    def clean_property_record(raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean a complete property record with all field types.

        Args:
            raw_data: Raw scraped data

        Returns:
            Cleaned and validated data dict

        Example:
            >>> raw = {
            ...     "address": "  123 Main St  ",
            ...     "price": "$450,000",
            ...     "bedrooms": "3 beds",
            ...     "sqft": "2,500 sqft"
            ... }
            >>> cleaned = DataValidator.clean_property_record(raw)
            >>> cleaned['price']
            450000.0
        """
        cleaned = {}

        # Clean address
        if 'address' in raw_data:
            cleaned['address'] = DataValidator.clean_address(raw_data['address'])

        # Clean price fields
        for price_field in ['price', 'estimated_value', 'list_price', 'sold_price']:
            if price_field in raw_data:
                cleaned[price_field] = DataValidator.clean_price(raw_data[price_field])

        # Clean numeric fields
        for numeric_field in ['bedrooms', 'sqft', 'year_built', 'lot_size']:
            if numeric_field in raw_data:
                cleaned[numeric_field] = DataValidator.clean_numeric(raw_data[numeric_field])

        # Clean float fields
        for float_field in ['bathrooms', 'acres']:
            if float_field in raw_data:
                cleaned[float_field] = DataValidator.clean_float(raw_data[float_field])

        # Clean dates
        for date_field in ['listing_date', 'auction_date', 'sold_date']:
            if date_field in raw_data:
                cleaned[date_field] = DataValidator.clean_date(raw_data[date_field])

        # Copy other fields as-is
        for field, value in raw_data.items():
            if field not in cleaned:
                cleaned[field] = value

        # Add metadata
        cleaned['_cleaned_at'] = datetime.now().isoformat()

        return cleaned

    @staticmethod
    def remove_empty_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove fields with None or empty values.

        Args:
            data: Data dict

        Returns:
            Data dict with empty fields removed
        """
        return {
            k: v for k, v in data.items()
            if v is not None and v != "" and v != []
        }


# Convenience function for quick access
def clean_property_record(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean a property record (convenience function).

    Args:
        raw_data: Raw scraped data

    Returns:
        Cleaned data dict
    """
    return DataValidator.clean_property_record(raw_data)
