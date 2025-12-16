"""
Site-specific scraper configurations.

This module contains CSS selectors, URLs, and site-specific settings
for each target website. Modify these when targeting new sites.
"""

# ===========================
# AUCTION SITE CONFIGURATION
# ===========================

AUCTION_CONFIG = {
    "name": "auction_scraper",
    "url": "https://www.auction.com/lp/foreclosures/",  # Public auction site for demo
    "description": "Scrapes real estate auction listings with appraisal PDFs",

    # CSS Selectors (customize based on target site structure)
    "selectors": {
        "property_card": "div.property-card, div[class*='listing'], article[class*='property']",
        "address": ".address, .property-address, [class*='address']",
        "price": ".price, .estimated-value, [class*='price']",
        "auction_date": ".auction-date, [class*='auction-date'], time",
        "pdf_link": "a[href$='.pdf'], a[class*='appraisal'], a[class*='document']",
        "next_button": "a.next, button.next, a[rel='next'], [aria-label='Next']",

        # Alternative selectors (fallback)
        "alt_property_card": "li[class*='property'], div[data-testid*='property']",
        "alt_price": "span[class*='price'], div[class*='value']",
    },

    # Pagination strategy: "button_click", "url_param", "infinite_scroll"
    "pagination": {
        "type": "button_click",
        "max_pages": 5,  # Limit for demo purposes
        "url_param_name": "page",  # If using url_param type
    },

    # Wait conditions
    "wait_for": {
        "selector": "div.property-card, div[class*='listing']",
        "timeout": 20000,  # milliseconds
    },

    # Data extraction patterns
    "patterns": {
        "price_regex": r"\$?([\d,]+\.?\d*)",
        "date_format": "%Y-%m-%d",
    },
}

# ===========================
# LISTING SITE CONFIGURATION
# ===========================

LISTING_CONFIG = {
    "name": "listing_scraper",
    "url": "https://www.realtor.com/realestateandhomes-search/New-York_NY",  # Public listing site
    "description": "Scrapes real estate listing data for comparable analysis",

    # Search parameters
    "search_params": {
        "zip": "10001",  # NYC zip code for demo
        "radius": 5,  # miles
        "min_price": 100000,
        "max_price": 2000000,
        "limit": 50,  # Max results to scrape
    },

    # CSS Selectors
    "selectors": {
        "listing_card": "div[class*='component_property-card'], li[class*='component_property-card']",
        "address": "[data-testid='property-address'], .card-address, div[class*='address']",
        "price": "[data-testid='property-price'], .card-price, div[class*='price']",
        "bedrooms": "[data-testid='property-bed'], .bed, span[class*='bed']",
        "bathrooms": "[data-testid='property-bath'], .bath, span[class*='bath']",
        "sqft": "[data-testid='property-sqft'], .sqft, span[class*='sqft']",
        "listing_date": ".listing-date, time, [class*='date']",
        "agent_contact": ".agent-info, [class*='agent']",
        "next_button": "a[aria-label='Next'], button.next-page, a[rel='next']",

        # Alternative selectors
        "alt_listing_card": "article[class*='property'], div[data-testid*='card']",
        "alt_price": "span[data-label='price'], div[class*='list-price']",
    },

    # Pagination
    "pagination": {
        "type": "button_click",
        "max_pages": 3,  # Limit for demo
        "url_param_name": "pg",
    },

    # Wait conditions
    "wait_for": {
        "selector": "div[class*='component_property-card'], li[class*='property']",
        "timeout": 20000,
    },

    # Data extraction patterns
    "patterns": {
        "price_regex": r"\$?([\d,]+\.?\d*)",
        "bed_regex": r"(\d+)\s*(?:bed|bd|bedroom)",
        "bath_regex": r"(\d+\.?\d*)\s*(?:bath|ba|bathroom)",
        "sqft_regex": r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|square feet)",
    },
}

# ===========================
# ADDITIONAL SITE CONFIGS
# ===========================

# You can add more site configurations here following the same pattern
# Example: Zillow, Redfin, Trulia, etc.

ZILLOW_CONFIG = {
    "name": "zillow_scraper",
    "url": "https://www.zillow.com/homes/",
    "description": "Scrapes Zillow listing data",
    # ... add selectors when needed
}

# Mapping of scraper names to configs
SCRAPER_CONFIGS = {
    "auction": AUCTION_CONFIG,
    "listing": LISTING_CONFIG,
    "zillow": ZILLOW_CONFIG,
}
