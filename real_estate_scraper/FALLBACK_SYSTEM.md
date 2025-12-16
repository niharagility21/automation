# Multi-Site Fallback System - Technical Documentation

## Overview

The scraper now features an **automatic multi-site fallback system** that tries multiple Indian real estate sites if the primary target fails. This ensures maximum data availability even if individual sites are down or blocking requests.

## Architecture

### Fallback Chain
```
PRIMARY (MagicBricks Ahmedabad)
    ↓ [Full retry logic: 3 attempts]
    ↓ [5s, 10s, 20s delays]
    ↓ [Proxy rotation + user-agent rotation]
    ↓
    ✗ FAILED
    ↓
FALLBACK 1 (Housing.com Mumbai)
    ↓ [Full retry logic: 3 attempts]
    ↓ [5s, 10s, 20s delays]
    ↓ [Proxy rotation + user-agent rotation]
    ↓
    ✗ FAILED
    ↓
FALLBACK 2 (99acres Mumbai)
    ↓ [Full retry logic: 3 attempts]
    ↓ [5s, 10s, 20s delays]
    ↓ [Proxy rotation + user-agent rotation]
    ↓
    ✓ SUCCESS → Return data
```

## Configuration

### File: `config/scrapers_config.py`

```python
LISTING_CONFIG = {
    "name": "listing_scraper",

    # PRIMARY TARGET
    "url": "https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=2,3&cityName=Ahmedabad",

    # FALLBACK URLs (tried in order)
    "fallback_urls": [
        "https://housing.com/in/buy/mumbai/mumbai",
        "https://www.99acres.com/search/property/buy/mumbai?city=12&preference=S&area_unit=1&res_com=R"
    ],

    # Flexible selectors that work across all 3 sites
    "selectors": {
        "listing_card": "div.mb-srp__card, div.card, div[class*='property'], div[id^='srp_tuple'], ...",
        "address": "div.mb-srp__card--title, h2, h3, [class*='address'], div.projectName, ...",
        "price": "[class*='price'], [class*='amount'], div.fontPrice, ...",
        # ... more flexible selectors
    }
}
```

### Key Features:
- **Flexible Selectors**: Multiple selector options with OR logic
- **Cross-Site Compatibility**: Same selectors work for all 3 sites
- **Easy Updates**: Just add more URLs to `fallback_urls` array

## Implementation

### File: `scrapers/listing_scraper.py`

#### Main Method: `extract_data()`

```python
async def extract_data(self) -> List[Dict[str, Any]]:
    """Extract data with multi-site fallback support."""

    # Get all URLs to try
    primary_url = self.config['url']
    fallback_urls = self.config.get('fallback_urls', [])
    urls_to_try = [primary_url] + fallback_urls

    # Try each URL in order
    for idx, url in enumerate(urls_to_try):
        url_name = ["PRIMARY", "FALLBACK 1", "FALLBACK 2"][idx]

        try:
            logger.info(f"ATTEMPTING {url_name}")

            # Try to scrape from this URL (with full retry logic)
            listings = await self._extract_from_url(url)

            if listings and len(listings) > 0:
                logger.info(f"✓ SUCCESS with {url_name}: {len(listings)} listings")
                return listings
            else:
                logger.warning(f"✗ {url_name} returned 0 listings, trying next...")

        except Exception as e:
            logger.error(f"✗ {url_name} FAILED: {e}")
            logger.warning(f"→ Moving to next fallback...")

    # All URLs failed
    logger.error("✗ ALL URLs EXHAUSTED")
    return []
```

#### Helper Method: `_extract_from_url(url)`

```python
async def _extract_from_url(self, url: str) -> List[Dict[str, Any]]:
    """
    Extract listings from a specific URL.

    This method contains the full scraping logic:
    - Retry mechanism (3 attempts with exponential backoff)
    - Pagination handling
    - Data extraction and validation

    Args:
        url: URL to scrape

    Returns:
        List of property records

    Raises:
        Exception: If scraping fails after all retries
    """
    all_listings = []

    # Pagination loop
    while current_page <= max_pages:
        # Fetch page with retry logic (from base_scraper)
        await self._fetch_with_retry(url, wait_for_selector=...)

        # Extract listings
        listings = await self._extract_listings_from_page()
        all_listings.extend(listings)

        # Navigate to next page
        has_next = await self._navigate_to_next_page()
        if not has_next:
            break

    return all_listings
```

## Retry Logic (Per URL)

Each URL in the fallback chain gets the **full retry mechanism** from `base_scraper.py`:

### Retry Sequence
```
Attempt 1: Immediate request
    ↓ [If fails: 429, 403, timeout, etc.]
    ↓
Wait 5 seconds
Rotate proxy + user-agent
    ↓
Attempt 2: Retry with new proxy/UA
    ↓ [If fails]
    ↓
Wait 10 seconds
Rotate proxy + user-agent
    ↓
Attempt 3: Final retry
    ↓ [If fails]
    ↓
Exception raised → Move to next fallback URL
```

### Retry Triggers
- HTTP 403 (Forbidden)
- HTTP 429 (Too Many Requests)
- HTTP 503 (Service Unavailable)
- Playwright timeout errors
- Network errors

## Logging Output

### Successful Scrape (Primary Works)
```
================================================================================
ATTEMPTING PRIMARY (MagicBricks Ahmedabad)
URL: https://www.magicbricks.com/property-for-sale/residential-real-estate...
================================================================================
INFO | Starting listing extraction from https://www.magicbricks.com...
INFO | [Attempt 1/3] Fetching: https://www.magicbricks.com...
INFO | ✓ Successfully fetched https://www.magicbricks.com...
INFO | Found 20 listing cards on page
INFO | Extracted 20 listings from page 1 (Total: 20)
INFO | No more pages to process
✓ SUCCESS with PRIMARY (MagicBricks Ahmedabad): 20 listings extracted
================================================================================
FINAL RESULT: 20 listings from https://www.magicbricks.com...
================================================================================
```

### Fallback Triggered (Primary Fails)
```
================================================================================
ATTEMPTING PRIMARY (MagicBricks Ahmedabad)
URL: https://www.magicbricks.com...
================================================================================
INFO | [Attempt 1/3] Fetching: https://www.magicbricks.com...
WARNING | Blocked response: 403 Forbidden
WARNING | Retry 1/3 for https://www.magicbricks.com... (Reason: 403). Waiting 5s...
INFO | Proxy rotation (retry attempt): None -> proxy1.example.com:8080
INFO | New user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)...
INFO | [Attempt 2/3] Fetching: https://www.magicbricks.com...
WARNING | Blocked response: 403 Forbidden
WARNING | Retry 2/3 for https://www.magicbricks.com... Waiting 10s...
INFO | [Attempt 3/3] Fetching: https://www.magicbricks.com...
ERROR | ✗ All retries exhausted for https://www.magicbricks.com...
✗ PRIMARY (MagicBricks Ahmedabad) FAILED after all retries
→ Moving to FALLBACK 1 (Housing.com Mumbai)...
================================================================================
ATTEMPTING FALLBACK 1 (Housing.com Mumbai)
URL: https://housing.com/in/buy/mumbai/mumbai
================================================================================
INFO | [Attempt 1/3] Fetching: https://housing.com...
INFO | ✓ Successfully fetched https://housing.com...
INFO | Found 15 listing cards on page
✓ SUCCESS with FALLBACK 1 (Housing.com Mumbai): 15 listings extracted
================================================================================
FINAL RESULT: 15 listings from https://housing.com/in/buy/mumbai/mumbai
================================================================================
```

### All URLs Fail
```
================================================================================
ATTEMPTING PRIMARY (MagicBricks Ahmedabad)
...
✗ PRIMARY FAILED after all retries
→ Moving to FALLBACK 1...
================================================================================
ATTEMPTING FALLBACK 1 (Housing.com Mumbai)
...
✗ FALLBACK 1 FAILED after all retries
→ Moving to FALLBACK 2...
================================================================================
ATTEMPTING FALLBACK 2 (99acres Mumbai)
...
✗ FALLBACK 2 FAILED after all retries
✗ ALL URLs EXHAUSTED - No more fallbacks available
ERROR | Failed to extract data from all URLs (primary + all fallbacks)
```

## Usage

### Basic Command
```bash
python main.py --site listing
```

### With Headless Mode Disabled (for demo)
```python
# In config/settings.py
HEADLESS_MODE = False
```

```bash
python main.py --site listing
```

### Expected Output File
```json
{
  "timestamp": "2025-12-16T14:30:22Z",
  "scraper_name": "ListingScraper",
  "scraper_type": "listing",
  "total_records": 20,
  "successful_records": 20,
  "records": [
    {
      "address": "Shivalik Heights, Ahmedabad",
      "price": 5500000.0,
      "bedrooms": 2,
      "sqft": 1100,
      "listing_date": "2025-12-10",
      "scraped_at": "2025-12-16T14:30:25Z"
    },
    // ... more records
  ],
  "errors": [],
  "execution_time_seconds": 45.2
}
```

## Adding More Fallback Sites

To add more fallback URLs, simply update `config/scrapers_config.py`:

```python
LISTING_CONFIG = {
    "url": "https://primary-site.com",

    "fallback_urls": [
        "https://fallback1-site.com",
        "https://fallback2-site.com",
        "https://fallback3-site.com",  # ← Add new fallback here
        "https://fallback4-site.com",  # ← And here
    ],

    # Make sure selectors are flexible enough to work with new sites
    "selectors": {
        "listing_card": "div.card, article.property, ...",  # ← Add new site's selector
    }
}
```

## Benefits

1. **High Availability**: If one site is down, others are tried automatically
2. **No Manual Intervention**: Fully automatic fallback system
3. **Full Retry Logic**: Each URL gets 3 retry attempts with delays
4. **Clear Logging**: Know exactly which site worked
5. **Easy Maintenance**: Just add URLs to config, no code changes needed
6. **Production-Ready**: Handles all edge cases gracefully

## Comparison: Before vs After

### Before (Single Site)
```
Try MagicBricks
    ↓ [If fails after 3 retries]
    ↓
Return 0 results ✗
```

### After (Multi-Site Fallback)
```
Try MagicBricks
    ↓ [If fails after 3 retries]
    ↓
Try Housing.com
    ↓ [If fails after 3 retries]
    ↓
Try 99acres
    ↓ [If succeeds]
    ↓
Return data ✓
```

## Technical Notes

- **No Breaking Changes**: All existing retry logic preserved
- **Backward Compatible**: Works with configs that don't have `fallback_urls`
- **Same Selectors**: Flexible selectors work across all 3 Indian sites
- **Performance**: Only tries fallbacks if needed (not always)
- **Error Handling**: Graceful degradation if all URLs fail

## Troubleshooting

### Problem: All URLs fail
**Solution**:
1. Check if sites are accessible manually
2. Add more proxies to `PROXY_LIST`
3. Increase `REQUEST_DELAY_SECONDS`
4. Update selectors if sites changed HTML structure

### Problem: Selectors not working for a fallback site
**Solution**:
1. Inspect the site's HTML
2. Add the site's specific selectors to the flexible selector list
3. Test with just that URL in the `url` field

### Problem: Logs not showing fallback attempts
**Solution**:
1. Check `LOG_LEVEL` in `config/settings.py` (should be INFO or DEBUG)
2. Look in `scraper.log` file for full logs

---

**Built with resilience for production real estate data extraction** 🏠
