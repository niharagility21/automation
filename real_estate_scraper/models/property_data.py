"""
Pydantic models for structured property data.

These models ensure type safety and validation for all scraped data,
providing a clean interface for downstream processing.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PropertyBase(BaseModel):
    """Base model with common property fields."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
    )

    address: str = Field(..., description="Property address", min_length=5)
    price: Optional[float] = Field(None, description="Listed or estimated price", ge=0)
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms", ge=0)
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms", ge=0)
    sqft: Optional[int] = Field(None, description="Square footage", ge=0)
    latitude: Optional[float] = Field(None, description="Latitude", ge=-90, le=90)
    longitude: Optional[float] = Field(None, description="Longitude", ge=-180, le=180)
    error: Optional[str] = Field(None, description="Error message if extraction failed")

    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Ensure address is not empty and has minimum length."""
        if not v or len(v.strip()) < 5:
            raise ValueError("Address must be at least 5 characters")
        return v.strip()


class AuctionProperty(PropertyBase):
    """Model for auction property data."""

    estimated_value: Optional[float] = Field(
        None,
        description="Estimated property value from appraisal",
        ge=0
    )
    auction_date: Optional[str] = Field(
        None,
        description="Scheduled auction date (ISO format)"
    )
    appraisal_source: Optional[str] = Field(
        None,
        description="Source of appraisal data (e.g., 'pdf', 'scrape')"
    )
    pdf_url: Optional[str] = Field(
        None,
        description="URL to appraisal PDF document"
    )
    pdf_path: Optional[str] = Field(
        None,
        description="Local path to downloaded PDF"
    )
    confidence_score: Optional[float] = Field(
        None,
        description="Confidence score for extracted data (0.0 to 1.0)",
        ge=0,
        le=1.0
    )
    property_type: Optional[str] = Field(
        None,
        description="Type of property (residential, commercial, etc.)"
    )
    auction_status: Optional[str] = Field(
        None,
        description="Status (upcoming, sold, cancelled)"
    )

    @field_validator('auction_date')
    @classmethod
    def validate_auction_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format."""
        if v is None:
            return v
        # Basic ISO date validation
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            # Try common formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y"]:
                try:
                    date_obj = datetime.strptime(v, fmt)
                    return date_obj.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return v  # Return as-is if can't parse


class ListingProperty(PropertyBase):
    """Model for real estate listing data."""

    list_price: Optional[float] = Field(
        None,
        description="Current listing price",
        ge=0
    )
    listing_date: Optional[str] = Field(
        None,
        description="Date property was listed (ISO format)"
    )
    days_on_market: Optional[int] = Field(
        None,
        description="Number of days on market",
        ge=0
    )
    agent_name: Optional[str] = Field(
        None,
        description="Listing agent name"
    )
    agent_contact: Optional[str] = Field(
        None,
        description="Agent contact info (phone/email)"
    )
    property_type: Optional[str] = Field(
        None,
        description="Type of property (house, condo, townhouse, etc.)"
    )
    listing_url: Optional[str] = Field(
        None,
        description="URL to full listing"
    )
    images: Optional[List[str]] = Field(
        default_factory=list,
        description="List of image URLs"
    )
    features: Optional[List[str]] = Field(
        default_factory=list,
        description="Property features (pool, garage, etc.)"
    )
    year_built: Optional[int] = Field(
        None,
        description="Year property was built",
        ge=1800,
        le=2100
    )
    lot_size: Optional[int] = Field(
        None,
        description="Lot size in square feet",
        ge=0
    )


class ScraperResult(BaseModel):
    """Model for complete scraper run result."""

    model_config = ConfigDict(validate_assignment=True)

    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of scraper run"
    )
    scraper_name: str = Field(
        ...,
        description="Name of scraper that ran"
    )
    scraper_type: str = Field(
        ...,
        description="Type of scraper (auction, listing, etc.)"
    )
    total_records: int = Field(
        0,
        description="Total number of records extracted",
        ge=0
    )
    successful_records: int = Field(
        0,
        description="Number of successfully extracted records",
        ge=0
    )
    failed_records: int = Field(
        0,
        description="Number of failed extractions",
        ge=0
    )
    records: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of property records"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of errors encountered"
    )
    execution_time_seconds: Optional[float] = Field(
        None,
        description="Total execution time",
        ge=0
    )
    proxy_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="Proxy rotation statistics"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    @field_validator('total_records')
    @classmethod
    def validate_total_matches_list(cls, v: int, info) -> int:
        """Ensure total_records matches length of records list."""
        records = info.data.get('records', [])
        if len(records) != v:
            # Auto-correct to match actual list length
            return len(records)
        return v


class ComparableAnalysis(BaseModel):
    """Model for comparable property analysis."""

    model_config = ConfigDict(validate_assignment=True)

    subject_property: Dict[str, Any] = Field(
        ...,
        description="The subject property being analyzed"
    )
    comparables: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of comparable properties"
    )
    median_price: Optional[float] = Field(
        None,
        description="Median price of comparables",
        ge=0
    )
    avg_price_per_sqft: Optional[float] = Field(
        None,
        description="Average price per square foot",
        ge=0
    )
    radius_miles: Optional[float] = Field(
        None,
        description="Search radius in miles",
        ge=0
    )
    analysis_date: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Date of analysis"
    )


class PDFExtractionResult(BaseModel):
    """Model for PDF extraction result."""

    model_config = ConfigDict(validate_assignment=True)

    pdf_path: str = Field(..., description="Path to PDF file")
    estimated_value: Optional[float] = Field(
        None,
        description="Extracted estimated value",
        ge=0
    )
    property_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted property details"
    )
    confidence_score: float = Field(
        0.0,
        description="Extraction confidence (0.0 to 1.0)",
        ge=0,
        le=1.0
    )
    source: str = Field(
        "pdf",
        description="Source type (pdf, ocr)"
    )
    extraction_method: Optional[str] = Field(
        None,
        description="Method used (PyPDF2, OCR)"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if extraction failed"
    )
    extracted_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of extraction"
    )
