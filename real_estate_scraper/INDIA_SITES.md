# Indian Real Estate Sites - Quick Reference

## 🚀 NEW: Multi-Site Fallback System

The scraper now **automatically tries multiple sites** if the primary fails!

**Command:** `python main.py --site listing`

### Fallback Order (Automatic):
1. **PRIMARY:** MagicBricks Ahmedabad (2-3 BHK) - Tries first with full retry logic
2. **FALLBACK 1:** Housing.com Mumbai - Tries if PRIMARY fails
3. **FALLBACK 2:** 99acres Mumbai - Tries if FALLBACK 1 fails

**How it works:**
- Each URL gets **full retry logic** (3 attempts with 5s, 10s, 20s delays)
- If PRIMARY fails after all retries → automatically tries FALLBACK 1
- If FALLBACK 1 fails → automatically tries FALLBACK 2
- Logs show exactly which site succeeded
- **No manual intervention needed!**

---

## Configured Sites

### 1. MagicBricks.com Ahmedabad (PRIMARY) ✅
**Command:** `python main.py --site listing`
- **URL:** https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=2,3&cityName=Ahmedabad
- **Target City:** Ahmedabad
- **Filter:** 2-3 BHK properties
- **Type:** India's 2nd largest real estate portal
- **Features:** Residential properties, builder info, agent contacts
- **Pagination:** Page buttons
- **Price Format:** ₹1.2 Cr, ₹45 Lac

**What it scrapes:**
- Property title and location
- Price (in Crores/Lakhs)
- BHK configuration (2-3 BHK)
- Carpet/Built-up area
- Listing date
- Builder/Agent contact

---

### 2. Housing.com Mumbai (FALLBACK 1) ✅
**Automatic if PRIMARY fails**
- **URL:** https://housing.com/in/buy/mumbai/mumbai
- **Target City:** Mumbai
- **Type:** Alternative if MagicBricks fails
- **Features:** Modern UI, data-testid selectors
- **Pagination:** Page buttons
- **Price Format:** ₹1.2 Cr, ₹45 Lac

---

### 3. 99acres.com Mumbai (FALLBACK 2) ✅
**Automatic if FALLBACK 1 fails**
- **URL:** https://www.99acres.com/search/property/buy/mumbai
- **Target City:** Mumbai
- **Type:** India's largest real estate portal (last resort)
- **Features:** Residential properties, BHK format
- **Pagination:** Infinite scroll
- **Price Format:** ₹1.2 Cr, ₹45 Lac

---

### 4. 99acres.com Mumbai (AUCTION SCRAPER) ✅
**Command:** `python main.py --site auction`
- **URL:** https://www.99acres.com/property-for-sale-flats-apartments-in-mumbai
- **Target City:** Mumbai
- **Type:** Separate scraper for auction/foreclosure properties
- **Features:** Residential properties, BHK format
- **Pagination:** Infinite scroll
- **Price Format:** ₹1.2 Cr, ₹45 Lac

---

## How to Run

### Quick Start (With Automatic Fallback)
```bash
# RECOMMENDED: Multi-site fallback scraper
# Tries MagicBricks → Housing.com → 99acres automatically
python main.py --site listing

# Alternative: 99acres only (no fallback)
python main.py --site auction

# Both scrapers
python main.py --site both
```

### Expected Behavior
When you run `python main.py --site listing`, you'll see:
```
================================================================================
ATTEMPTING PRIMARY (MagicBricks Ahmedabad)
URL: https://www.magicbricks.com/property-for-sale/residential-real-estate...
================================================================================
INFO | Fetching: https://www.magicbricks.com...
[Retry attempts with 5s, 10s, 20s delays if needed]
✓ SUCCESS with PRIMARY (MagicBricks Ahmedabad): 25 listings extracted
================================================================================
FINAL RESULT: 25 listings from https://www.magicbricks.com...
================================================================================
```

**If PRIMARY fails:**
```
✗ PRIMARY (MagicBricks Ahmedabad) FAILED after all retries
→ Moving to FALLBACK 1 (Housing.com Mumbai)...
================================================================================
ATTEMPTING FALLBACK 1 (Housing.com Mumbai)
...
```

### Before Running
1. **Disable headless mode** to see the browser (for demo):
   ```python
   # In config/settings.py
   HEADLESS_MODE = False  # Set to False
   ```

2. **Optional: Add proxies** (if you want to avoid rate limiting):
   ```python
   # In config/settings.py
   PROXY_LIST = [
       "http://user:pass@your-indian-proxy.com:8080",
   ]
   ```

---

## Updating Selectors (If Sites Change)

### Step 1: Inspect the Site
1. Open the URL in Chrome/Firefox
2. Right-click on a property card → **Inspect**
3. Find the main container div (usually has a unique class)

### Step 2: Update Config
Edit `config/scrapers_config.py`:

```python
# For 99acres
AUCTION_CONFIG = {
    "selectors": {
        "property_card": "div.NEW_CLASS_NAME",  # Update this
        "address": "div.NEW_ADDRESS_CLASS",     # Update this
        # ... etc
    }
}
```

### Step 3: Test
```bash
python main.py --site auction
```

Check the logs - if you see "Found 0 property cards", your selectors need updating.

---

## Indian Price Format Examples

The scraper now handles Indian number formats:

| Input | Output |
|-------|--------|
| `₹1.2 Cr` | 12,000,000 |
| `₹1.2 Crore` | 12,000,000 |
| `₹45 Lac` | 4,500,000 |
| `₹45 Lakh` | 4,500,000 |
| `₹1.5 L` | 150,000 |
| `₹50 K` | 50,000 |

These are automatically converted to numeric values in the output JSON.

---

## Troubleshooting

### Problem: No property cards found
**Solution:** Update selectors in `config/scrapers_config.py`
1. Inspect the site
2. Find the actual class names
3. Update the config
4. Re-run

### Problem: Prices not parsing correctly
**Solution:** Check the price format on the site
1. If format changed, update `patterns.price_regex` in config
2. The validator handles Cr, Crore, Lac, Lakh, L, K formats

### Problem: Infinite scroll not working
**Solution:** Try changing pagination type
```python
"pagination": {
    "type": "button_click",  # Try this instead of infinite_scroll
}
```

### Problem: Site blocking requests
**Solution:**
1. Add delays: Increase `REQUEST_DELAY_SECONDS` in `config/settings.py`
2. Add proxies: Update `PROXY_LIST` with Indian residential proxies
3. Rotate user-agents: Already configured in `config/settings.py`

---

## Expected Output

```json
{
  "timestamp": "2025-12-16T14:30:22Z",
  "scraper_name": "AuctionScraper",
  "scraper_type": "auction",
  "total_records": 15,
  "records": [
    {
      "address": "Lodha Amara, Thane West, Mumbai",
      "price": 12000000.0,
      "bedrooms": 3,
      "sqft": 1200,
      "scraped_at": "2025-12-16T14:30:25Z"
    }
  ]
}
```

---

## Cities You Can Target

Just change the URL in `config/scrapers_config.py`:

### 99acres
- Mumbai: `/property-for-sale-flats-apartments-in-mumbai`
- Delhi: `/property-for-sale-flats-apartments-in-delhi`
- Bangalore: `/property-for-sale-flats-apartments-in-bangalore`
- Pune: `/property-for-sale-flats-apartments-in-pune`

### MagicBricks
- Change `cityName=Mumbai` to:
  - `cityName=Delhi`
  - `cityName=Bangalore`
  - `cityName=Pune`

---

## Tips for Loom Demo

1. **Set headless=False** so browser is visible
2. **Use 99acres** - most reliable
3. **Show logs** - retry logic, proxy rotation visible
4. **Limit pages** - Set `max_pages=2` for faster demo
5. **Show JSON output** - Clean, structured Indian property data

---

## Need Help?

1. Check main `README.md` for architecture details
2. Check logs in `scraper.log`
3. Inspect the target site for correct selectors
4. All retry logic, proxy rotation, anti-bot detection stays the same - only configs change!
