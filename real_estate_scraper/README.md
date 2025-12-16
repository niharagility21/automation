# Real Estate Scraper - Production-Grade Web Scraping

A production-ready real estate scraper built with Playwright for scraping auction sites and real estate listings. Features robust anti-bot detection, retry logic with exponential backoff, proxy rotation, and PDF parsing capabilities.

## 🚀 Features

### Core Capabilities
- **Dual Scraper System**: Auction properties + Real estate listings
- **Anti-Bot Detection**: Proxy rotation, user-agent spoofing, anti-detection headers
- **Retry Logic**: Exponential backoff (5s → 10s → 20s) with automatic proxy rotation
- **PDF Parsing**: Extract appraisal values from PDF documents (PyPDF2 + OCR fallback)
- **Data Validation**: Type-safe Pydantic models with automatic cleaning
- **Structured Logging**: Color-coded console + file logging with timestamps
- **Export to JSON**: Clean, structured output for downstream processing

### Technical Highlights
- **Async/Await**: Full async implementation with Playwright
- **Modular Architecture**: Clean separation of concerns (scrapers, utils, config, models)
- **Type Safety**: Comprehensive type hints and Pydantic validation
- **Error Handling**: Graceful degradation with detailed error logging
- **Production-Ready**: Configurable timeouts, rate limiting, and proxy management

---

## 📁 Project Structure

```
real_estate_scraper/
├── config/
│   ├── __init__.py
│   ├── settings.py                 # Global settings (proxies, timeouts, etc.)
│   └── scrapers_config.py          # Site-specific selectors and configs
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py             # Abstract base with retry logic
│   ├── auction_scraper.py          # Auction site scraper
│   └── listing_scraper.py          # Listing site scraper
├── utils/
│   ├── __init__.py
│   ├── logger.py                   # Logging configuration
│   ├── proxy_rotator.py            # Proxy rotation + user-agent management
│   ├── pdf_parser.py               # PDF extraction + OCR
│   └── data_validator.py           # Data cleaning and validation
├── models/
│   ├── __init__.py
│   └── property_data.py            # Pydantic data models
├── output/                         # Generated output files (JSON, PDFs)
├── main.py                         # Entry point
├── requirements.txt                # Dependencies
└── README.md                       # This file
```

---

## 🛠️ Installation

### 1. Clone the Repository
```bash
cd real_estate_scraper
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers
```bash
playwright install chromium
```

### 5. Optional: Install Tesseract for OCR
**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

---

## 🚦 Quick Start

### Run Auction Scraper
```bash
python main.py --site auction
```

### Run Listing Scraper
```bash
python main.py --site listing
```

### Run Both Scrapers
```bash
python main.py --site both
```

### Output
Results are saved to `output/output_<type>_<timestamp>.json`

Example:
```
output/output_auction_20251216_143022.json
```

---

## ⚙️ Configuration

### Global Settings (`config/settings.py`)

**Key Settings:**
- `HEADLESS_MODE`: Run browser headless (True) or visible (False)
- `MAX_RETRIES`: Number of retry attempts (default: 3)
- `RETRY_DELAYS`: Delays between retries in seconds (default: [5, 10, 20])
- `BROWSER_TIMEOUT`: Page load timeout in milliseconds (default: 20000)
- `PROXY_LIST`: List of proxy URLs
- `USER_AGENT_POOL`: List of user-agent strings
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

**Example Proxy Configuration:**
```python
PROXY_LIST = [
    "http://user:pass@proxy1.brightdata.com:22225",
    "http://user:pass@proxy2.brightdata.com:22225",
]
```

### Site-Specific Config (`config/scrapers_config.py`)

**Customize for Your Target Sites:**

```python
AUCTION_CONFIG = {
    "url": "https://www.example-auction.com/listings",
    "selectors": {
        "property_card": "div.property-card",
        "address": ".property-address",
        "price": ".estimated-value",
        "pdf_link": "a.appraisal-pdf",
        "next_button": "a.next-page"
    },
    "pagination": {
        "type": "button_click",  # or "url_param", "infinite_scroll"
        "max_pages": 5,
    }
}
```

**Update selectors to match your target site's HTML structure.**

---

## 🔄 How It Works

### 1. Retry Logic (Core Feature)

**Exponential Backoff Strategy:**
```
Attempt 1: Immediate request
    ↓ (fails)
Attempt 2: Wait 5s, rotate proxy + user-agent, retry
    ↓ (fails)
Attempt 3: Wait 10s, rotate proxy + user-agent, retry
    ↓ (fails)
Attempt 4: Wait 20s, rotate proxy + user-agent, final retry
    ↓ (fails)
Exception raised
```

**Triggers for Retry:**
- HTTP 403 (Forbidden)
- HTTP 429 (Too Many Requests)
- HTTP 503 (Service Unavailable)
- Timeout errors
- Network errors

**Implementation:**
See `scrapers/base_scraper.py` → `_fetch_with_retry()` method

### 2. Proxy Rotation

**Strategy:**
- **Round-robin rotation**: Each request gets the next proxy in the list
- **Failure tracking**: Proxies are removed after 3 consecutive failures
- **Automatic rotation on retry**: Fresh proxy for each retry attempt

**Implementation:**
See `utils/proxy_rotator.py` → `ProxyRotator` class

### 3. Anti-Bot Detection

**Techniques:**
- Randomized user-agents (Chrome, Firefox, Safari, Edge)
- Randomized viewport sizes (1920x1080, 1366x768, etc.)
- Realistic headers (Accept-Language, DNT, Connection)
- Geolocation spoofing
- JavaScript overrides (hide webdriver property)

**Implementation:**
See `utils/proxy_rotator.py` → `get_browser_context_config()`

### 4. PDF Parsing

**Process:**
1. Download PDF from URL
2. Extract text using PyPDF2
3. If text extraction fails → fall back to OCR (Tesseract)
4. Use regex patterns to find appraisal values
5. Return structured data with confidence score

**Patterns Matched:**
- Estimated value
- Appraised value
- Market value
- Property address
- Bedrooms, bathrooms, square footage

**Implementation:**
See `utils/pdf_parser.py` → `PDFParser` class

---

## 📊 Output Format

**Example JSON Output:**

```json
{
  "timestamp": "2025-12-16T14:30:22.123456",
  "scraper_name": "AuctionScraper",
  "scraper_type": "auction",
  "total_records": 15,
  "successful_records": 14,
  "failed_records": 1,
  "execution_time_seconds": 45.67,
  "records": [
    {
      "address": "123 Main St, New York, NY 10001",
      "price": 450000.0,
      "estimated_value": 475000.0,
      "auction_date": "2025-12-20",
      "bedrooms": 3,
      "bathrooms": 2.0,
      "sqft": 2500,
      "appraisal_source": "pdf",
      "confidence_score": 0.85,
      "pdf_path": "/path/to/output/pdfs/auction_0_20251216_143022.pdf",
      "scraped_at": "2025-12-16T14:30:25.456789",
      "_cleaned_at": "2025-12-16T14:30:25.567890"
    }
  ],
  "errors": [],
  "proxy_stats": {
    "total_configured": 5,
    "active_proxies": 4,
    "removed_proxies": 1,
    "failure_counts": {}
  }
}
```

---

## 🧪 Testing

### Test with Demo Mode (No Proxies)
1. Set `PROXY_LIST = []` in `config/settings.py`
2. Set `HEADLESS_MODE = False` to see browser
3. Run: `python main.py --site auction`
4. Watch the browser interact with the site

### Test Retry Logic
1. Use an invalid URL or block your IP temporarily
2. Watch logs for retry attempts with exponential backoff
3. See proxy rotation in action

### Test PDF Parsing
1. Add a real PDF URL to the config
2. Run the scraper
3. Check `output/pdfs/` for downloaded PDFs
4. Check JSON output for extracted appraisal values

---

## 🎥 Loom Demo Script

### 1. IDE Overview (1 min)
- Open project in VS Code/PyCharm
- Show directory structure
- Explain modular organization (config, scrapers, utils, models)

### 2. Retry Logic Deep Dive (2 min)
- Open `scrapers/base_scraper.py`
- Show `_fetch_with_retry()` method
- Highlight exponential backoff delays: [5, 10, 20]
- Point out proxy rotation on each retry
- Show logging statements

### 3. Proxy Rotation Function (1 min)
- Open `utils/proxy_rotator.py`
- Show `get_next_proxy()` round-robin logic
- Show failure tracking and removal
- Explain fallback behavior

### 4. Live Demo (2-3 min)
- Open terminal
- Run: `python main.py --site auction`
- **Show browser window** (not headless) interacting with site
- **Show terminal logs** with timestamps, retry attempts, proxy rotations
- Wait for completion
- Show output JSON file: `cat output/output_auction_*.json | jq`
- Highlight structured data

### 5. Q&A Ready (1 min)
- Summarize: "This handles all Block 3 requirements"
- Mention: "Block 4 valuation engine builds on this clean data"

---

## 🔧 Troubleshooting

### Common Issues

**1. Playwright not installed:**
```bash
playwright install chromium
```

**2. Tesseract not found (for OCR):**
- Install Tesseract (see Installation section)
- Update `TESSERACT_CMD` in `config/settings.py`

**3. No data extracted:**
- Check selectors in `config/scrapers_config.py`
- Inspect target site's HTML structure
- Update selectors to match

**4. All proxies removed:**
- Check proxy credentials
- Verify proxies are working
- Increase `PROXY_FAILURE_THRESHOLD` in settings

**5. Rate limiting / IP blocked:**
- Add more proxies to `PROXY_LIST`
- Increase `REQUEST_DELAY_SECONDS`
- Enable headless mode: `HEADLESS_MODE = True`

---

## 🚀 Next Steps

### Integration with Valuation Engine (Block 4)
1. **Load scraped data**: Read JSON output from `output/` directory
2. **Run comparable analysis**: Use `ListingScraper` data for comps
3. **Apply valuation models**: ARV calculation, flip analysis
4. **Export valuations**: Save to database or API

### Production Deployment
1. **Dockerize**: Create Dockerfile with Playwright
2. **Scheduler**: Use cron or Celery for periodic scraping
3. **Database**: Store results in PostgreSQL/MongoDB
4. **Monitoring**: Add Sentry for error tracking
5. **API**: Expose scraped data via FastAPI/Flask

### Enhancements
- [ ] Add more scraper targets (Zillow, Redfin, Trulia)
- [ ] Implement geolocation-based filtering
- [ ] Add image downloading and analysis
- [ ] Create dashboard for results visualization
- [ ] Add webhook notifications on completion

---

## 📝 License

This project is for educational and authorized use only. Always respect robots.txt and terms of service of target websites.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 📧 Support

For issues or questions:
- Open a GitHub issue
- Check logs in `scraper.log`
- Review configuration in `config/`

---

**Built with ❤️ for production-grade real estate data extraction**
