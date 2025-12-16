"""
Global settings and configuration for the real estate scraper.

This module contains all environment-level settings including proxy lists,
API keys, timeout values, and general scraper configuration.
"""

import os
from typing import List, Optional
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Output directory for scraped data
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
LOG_FILE = BASE_DIR / "scraper.log"

# Browser Configuration
HEADLESS_MODE = os.getenv("HEADLESS_MODE", "False").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "20000"))  # milliseconds

# Retry Configuration
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAYS = [5, 10, 20]  # seconds for exponential backoff

# Proxy Configuration
# Format: http://user:pass@proxy:port or http://proxy:port
PROXY_LIST: List[str] = [
    # Example proxies - replace with real ones from Bright Data, Oxylabs, etc.
    # "http://user:pass@proxy1.brightdata.com:22225",
    # "http://user:pass@proxy2.brightdata.com:22225",
    # Leave empty for demo/testing without proxies
]

# Proxy failure threshold - remove proxy after this many consecutive failures
PROXY_FAILURE_THRESHOLD = 3

# User-Agent Pool (realistic browsers)
USER_AGENT_POOL: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Viewport sizes (common screen resolutions)
VIEWPORT_SIZES: List[dict] = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 2560, "height": 1440},
]

# Anti-Detection Headers
EXTRA_HTTP_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Geolocation (NYC by default - can randomize per request)
DEFAULT_GEOLOCATION = {
    "latitude": 40.7128,
    "longitude": -74.0060,
}

TIMEZONE_ID = "America/New_York"

# PDF Processing
PDF_DOWNLOAD_DIR = OUTPUT_DIR / "pdfs"
PDF_DOWNLOAD_DIR.mkdir(exist_ok=True)

# OCR Configuration (if PyPDF2 text extraction fails)
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")  # Linux default

# Data Validation
REQUIRED_FIELDS = ["address"]  # Minimum required fields for valid record
DEFAULT_VALUES = {
    "estimated_value": None,
    "bedrooms": None,
    "bathrooms": None,
    "sqft": None,
}

# Rate Limiting (delay between requests to same domain)
REQUEST_DELAY_SECONDS = 2

# Concurrency
MAX_CONCURRENT_REQUESTS = 3
