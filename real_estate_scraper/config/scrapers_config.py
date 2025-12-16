"""
Site-specific scraper configurations.

This module contains CSS selectors, URLs, and site-specific settings
for each target website. Modify these when targeting new sites.
"""

# ===========================
# 99ACRES.COM CONFIGURATION (INDIA)
# ===========================
# 99acres.com is India's largest real estate portal - works great from India
# URL: https://www.99acres.com/property-for-sale-flats-apartments-in-mumbai
#
# HOW TO UPDATE SELECTORS:
# 1. Open the URL in your browser
# 2. Right-click on a property card → Inspect
# 3. Find the container div class (usually starts with 'srp_tuple' or 'tupleNew')
# 4. Update the selectors below with the actual class names

AUCTION_CONFIG = {
    "name": "auction_scraper",
    "url": "https://www.99acres.com/property-for-sale-flats-apartments-in-mumbai",
    "description": "Scrapes real estate listings from 99acres.com (India's largest property portal)",

    # CSS Selectors for 99acres.com
    "selectors": {
        # Main property card container
        "property_card": "div[id^='srp_tuple'], div.srpTuple, div.tupleNew, div.tuple_srp_new, section[class*='srpCard']",

        # Property address/location (project name + area)
        "address": "div.projectName, h2.projectName a, div.tuple_area, span.projectName, div.caption_location, span.ellipsis",

        # Price (in Crores/Lakhs)
        "price": "div.price, span.price, div.srpPrice, span.amount, td.price, div.fontPrice, span.srpPriceValue",

        # BHK configuration (1BHK, 2BHK, 3BHK, 4BHK - Indian format)
        "bedrooms": "div.BHK, span.BHK, div.tupleDetail, span.bedrooms, div.bed_config, span.caption_srp_bd_bath",

        # Square footage (Super built-up area)
        "sqft": "div.area, span.buArea, div.srpSize, span.sqft, div.superBuiltupArea, td[title*='Built']",

        # Posted date / listing date
        "auction_date": "div.posted, span.postedOn, div.datePasted, time, span.listing_date, div.posted_time",

        # Brochure/PDF download link (if available)
        "pdf_link": "a[href$='.pdf'], a[class*='brochure'], a[class*='document'], a[title*='Download'], a.downloadBrochure",

        # Next page button (99acres uses infinite scroll mostly)
        "next_button": "a.next, button.next, a[rel='next'], div.pagination a.next, button[aria-label='Next']",

        # Alternative selectors (fallback if main ones don't work)
        "alt_property_card": "div.srpWrap, div.clearfix.srpWrap, section.srpCard, article[class*='property']",
        "alt_price": "span.srpPriceValue, div.priceWrap, span.fontPrice, td.price span",
        "alt_bedrooms": "span.caption_srp_bd_bath, div.bed_config, td.configTd",
    },

    # Pagination strategy
    "pagination": {
        "type": "infinite_scroll",  # 99acres primarily uses infinite scroll
        "max_pages": 5,  # Number of scroll attempts
        "url_param_name": "page",  # Fallback if URL pagination is used
    },

    # Wait conditions
    "wait_for": {
        "selector": "div[id^='srp_tuple'], div.srpTuple, section.srpCard",
        "timeout": 20000,  # milliseconds
    },

    # Data extraction patterns (Indian Rupees: ₹)
    "patterns": {
        # Indian price formats: ₹1.2 Cr, ₹45 Lac, ₹45 Lakh, ₹1.5 L
        "price_regex": r"₹\s?([\d,\.]+)\s*(?:Cr|Crore|Lac|Lakh|L|K)?",
        "bhk_regex": r"(\d+)\s*BHK",  # 2 BHK, 3 BHK, etc.
        "sqft_regex": r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|Sq-ft|Sq\.Ft\.)",
        "date_format": "%Y-%m-%d",
    },
}

# ===========================
# INDIAN REAL ESTATE SITES - MULTI-FALLBACK CONFIGURATION
# ===========================
# PRIMARY: MagicBricks Ahmedabad (2-3 BHK properties)
# FALLBACK 1: Housing.com Mumbai
# FALLBACK 2: 99acres Mumbai
#
# HOW TO UPDATE SELECTORS:
# 1. Open each URL in your browser
# 2. Right-click on a property card → Inspect
# 3. Find the container div class
# 4. Update the selectors below with the actual class names

LISTING_CONFIG = {
    "name": "listing_scraper",

    # PRIMARY TARGET: MagicBricks Ahmedabad (2-3 BHK)
    "url": "https://www.magicbricks.com/property-for-sale/residential-real-estate?bedroom=2,3&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villa&cityName=Ahmedabad",

    # FALLBACK URLs (tried in order if primary fails after all retries)
    "fallback_urls": [
        "https://housing.com/in/buy/mumbai/mumbai",
        "https://www.99acres.com/search/property/buy/mumbai?city=12&preference=S&area_unit=1&res_com=R"
    ],

    "description": "Scrapes Indian real estate listings with multi-site fallback support",

    # Search parameters
    "search_params": {
        "city": "Ahmedabad",  # Primary: Ahmedabad, Fallbacks: Mumbai
        "bedrooms": "2,3",  # 2-3 BHK
        "min_price": 1000000,  # ₹10 Lakh
        "max_price": 50000000,  # ₹5 Crore
        "limit": 50,  # Max results to scrape
    },

    # CSS Selectors - FLEXIBLE (works across MagicBricks, Housing.com, 99acres)
    # Multiple selectors with OR logic for robustness
    "selectors": {
        # Main listing card container (flexible for all 3 sites)
        "listing_card": "div.mb-srp__card, div[class*='mb-srp__card'], div.card, div[class*='property'], article[class*='listing'], div[id^='srp_tuple'], div.srpTuple, section[class*='snb-card'], div[data-testid='builder-card']",

        # Property address/location (flexible)
        "address": "div.mb-srp__card--title, h2.mb-srp__card--title, h2, h3, [class*='address'], [class*='location'], div.projectName, span.projectName, div[data-testid='builder-card-name'], div.locality, div[class*='title']",

        # Price (flexible for all Indian sites)
        "price": "div.mb-srp__card__price--amount, span.mb-srp__card__price, [class*='price'], [class*='amount'], span[class*='cost'], div.fontPrice, span.srpPriceValue, div[data-testid='builder-card-price']",

        # BHK/Bedrooms (Indian format)
        "bedrooms": "div.mb-srp__card__summary--value, span[class*='bedroom'], [class*='bhk'], span[class*='bed'], div.BHK, span.BHK, div[data-testid='bhk'], div.bed_config",

        # Square footage
        "sqft": "div.mb-srp__card__summary--value, span[class*='area'], [class*='sqft'], [class*='sq-ft'], div[title*='Carpet'], div[title*='Built'], span.buArea, div[data-testid='carpet-area']",

        # Listing date
        "listing_date": "div.mb-srp__card__posted--date, span.mb-srp__card__ads--posted, [class*='date'], [class*='posted'], span[class*='time'], time, div.posted, span.postedOn",

        # Agent/builder info
        "agent_contact": "div.mb-srp__card__ads--phone, span.mb-srp__card__builder, [class*='builder-name'], [class*='agent'], div.builder-name, span.agent-name",

        # Next page button (flexible)
        "next_button": "a.mb-srp__pagination--next, a[rel='next'], button[aria-label='Next'], a.next-page, div.pagination a.next, button.next, a.next",

        # Alternative selectors (fallback)
        "alt_listing_card": "div.m-srp-card, div[class*='m-srp-card'], article[class*='property-card'], div.srpWrap, section.srpCard",
        "alt_price": "span.mb-srp__card__price--amount, div[data-price], span[class*='price'], td.price span",
    },

    # Pagination
    "pagination": {
        "type": "button_click",  # Works for MagicBricks and Housing.com
        "max_pages": 3,  # Limit for demo
        "url_param_name": "page",
    },

    # Wait conditions (flexible selector that works across sites)
    "wait_for": {
        "selector": "div.mb-srp__card, div[class*='mb-srp__card'], div.card, div[class*='property'], div[id^='srp_tuple']",
        "timeout": 20000,
    },

    # Data extraction patterns (Indian Rupees)
    "patterns": {
        # Indian price formats: ₹1.2 Cr, ₹45 Lac
        "price_regex": r"₹\s?([\d,\.]+)\s*(?:Cr|Crore|Lac|Lakh|L|K)?",
        "bed_regex": r"(\d+)\s*(?:BHK|bed|bd|bedroom)",
        "bath_regex": r"(\d+\.?\d*)\s*(?:bath|ba|bathroom)",
        "sqft_regex": r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|Sq-ft|Sq\.Ft\.)",
    },
}

# ===========================
# ADDITIONAL SITE CONFIGS (INDIA)
# ===========================

# HOUSING.COM - FALLBACK OPTION (INDIA)
# Works great from India, another major portal
HOUSING_CONFIG = {
    "name": "housing_scraper",
    "url": "https://housing.com/in/buy/real-estate-mumbai",
    "description": "Scrapes Housing.com listing data (fallback option)",

    # Search parameters
    "search_params": {
        "city": "Mumbai",
        "min_price": 1000000,  # ₹10 Lakh
        "max_price": 50000000,  # ₹5 Crore
        "limit": 50,
    },

    # CSS Selectors for Housing.com
    "selectors": {
        "listing_card": "div[data-testid='builder-card'], div.card, div[class*='snb-card']",
        "address": "div[data-testid='builder-card-name'], h2.heading-6, div.locality",
        "price": "div[data-testid='builder-card-price'], span.price, div[class*='price']",
        "bedrooms": "div[data-testid='bhk'], span[class*='bhk'], div.config",
        "sqft": "div[data-testid='carpet-area'], span[class*='area'], div.super-area",
        "listing_date": "div.posted-on, time, span[class*='date']",
        "agent_contact": "div.builder-name, span.agent-name",
        "next_button": "button[aria-label='Next'], a.next-page, div.pagination button:last-child",

        # Alternative selectors
        "alt_listing_card": "article[class*='property'], div[class*='listing-card']",
        "alt_price": "span[data-price], div[class*='price-value']",
    },

    # Pagination
    "pagination": {
        "type": "button_click",
        "max_pages": 3,
        "url_param_name": "page",
    },

    # Wait conditions
    "wait_for": {
        "selector": "div[data-testid='builder-card'], div.card",
        "timeout": 20000,
    },

    # Data extraction patterns
    "patterns": {
        "price_regex": r"₹\s?([\d,\.]+)\s*(?:Cr|Crore|Lac|Lakh|L|K)?",
        "bed_regex": r"(\d+)\s*(?:BHK|bed|bd|bedroom)",
        "bath_regex": r"(\d+\.?\d*)\s*(?:bath|ba|bathroom)",
        "sqft_regex": r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|Sq-ft|Sq\.Ft\.)",
    },
}

# Mapping of scraper names to configs
SCRAPER_CONFIGS = {
    "auction": AUCTION_CONFIG,      # 99acres.com
    "listing": LISTING_CONFIG,      # MagicBricks.com
    "housing": HOUSING_CONFIG,      # Housing.com (fallback)
}
