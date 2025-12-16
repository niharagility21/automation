"""
Real estate listing site scraper for market comparables.

Extracts:
- Property addresses
- List prices
- Bedrooms, bathrooms, square footage
- Listing dates
- Agent information

Used for comparable property analysis and market valuation.
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import statistics

from scrapers.base_scraper import BaseScraper
from utils.logger import setup_logger
from utils.data_validator import clean_property_record

logger = setup_logger(__name__)


class ListingScraper(BaseScraper):
    """
    Scraper for real estate listing sites (Zillow, Realtor.com, etc.).

    Inherits retry logic and browser management from BaseScraper.
    Implements listing-specific data extraction and comparable analysis.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize listing scraper.

        Args:
            config: Listing site configuration from scrapers_config.py
        """
        super().__init__(name="ListingScraper", config=config)
        self.search_params = config.get('search_params', {})

    async def extract_data(self) -> List[Dict[str, Any]]:
        """
        Extract listing data from target site with fallback support.

        Returns:
            List of listing property records

        Process:
        1. Try PRIMARY URL with full retry logic
        2. If PRIMARY fails, try FALLBACK 1 with full retry logic
        3. If FALLBACK 1 fails, try FALLBACK 2 with full retry logic
        4. Extract listing data from whichever URL succeeds
        5. Calculate market statistics
        """
        all_listings = []

        # Get fallback URLs from config
        primary_url = self.config['url']
        fallback_urls = self.config.get('fallback_urls', [])

        # Try primary URL first, then fallbacks
        urls_to_try = [primary_url] + fallback_urls
        url_names = ["PRIMARY (MagicBricks Ahmedabad)", "FALLBACK 1 (Housing.com Mumbai)", "FALLBACK 2 (99acres Mumbai)"]

        successful_url = None

        for idx, url in enumerate(urls_to_try):
            url_name = url_names[idx] if idx < len(url_names) else f"FALLBACK {idx}"

            try:
                logger.info("=" * 80)
                logger.info(f"ATTEMPTING {url_name}")
                logger.info(f"URL: {url}")
                logger.info("=" * 80)

                # Try to scrape from this URL
                listings = await self._extract_from_url(url)

                if listings and len(listings) > 0:
                    logger.info(f"✓ SUCCESS with {url_name}: {len(listings)} listings extracted")
                    all_listings = listings
                    successful_url = url
                    break
                else:
                    logger.warning(f"✗ {url_name} returned 0 listings, trying next fallback...")

            except Exception as e:
                logger.error(f"✗ {url_name} FAILED after all retries: {e}")

                if idx < len(urls_to_try) - 1:
                    next_name = url_names[idx + 1] if idx + 1 < len(url_names) else f"FALLBACK {idx + 1}"
                    logger.warning(f"→ Moving to {next_name}...")
                else:
                    logger.error("✗ ALL URLs EXHAUSTED - No more fallbacks available")

        # Check if we got any data
        if not all_listings:
            error_msg = "Failed to extract data from all URLs (primary + all fallbacks)"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return []

        logger.info("=" * 80)
        logger.info(f"FINAL RESULT: {len(all_listings)} listings from {successful_url}")
        logger.info("=" * 80)

        return all_listings

    async def _extract_from_url(self, url: str) -> List[Dict[str, Any]]:
        """
        Extract listings from a specific URL.

        This method tries to scrape from the given URL with full retry logic.

        Args:
            url: URL to scrape

        Returns:
            List of listing records

        Raises:
            Exception: If scraping fails after all retries
        """
        all_listings = []
        current_page = 1
        max_pages = self.config.get('pagination', {}).get('max_pages', 3)
        max_results = self.search_params.get('limit', 50)

        logger.info(
            f"Starting listing extraction from {url} "
            f"(params: {self.search_params})"
        )

        # Use the provided URL directly (already has query params)
        search_url = url

        while current_page <= max_pages and len(all_listings) < max_results:
            try:
                logger.info(
                    f"Processing page {current_page}/{max_pages} "
                    f"(collected: {len(all_listings)}/{max_results})"
                )

                # Fetch page with retry logic
                await self._fetch_with_retry(
                    url=search_url,
                    wait_for_selector=self.config['wait_for']['selector']
                )

                # Extract listings from current page
                listings = await self._extract_listings_from_page()
                all_listings.extend(listings)

                logger.info(
                    f"Extracted {len(listings)} listings from page {current_page} "
                    f"(Total: {len(all_listings)})"
                )

                # Stop if we've reached the limit
                if len(all_listings) >= max_results:
                    logger.info(f"Reached limit of {max_results} results")
                    break

                # Try to navigate to next page
                has_next = await self._navigate_to_next_page()
                if not has_next:
                    logger.info("No more pages to process")
                    break

                current_page += 1

                # Update search URL if pagination changes URL
                search_url = self.page.url

                # Be polite - wait between pages
                await self.wait_politely(2)

            except Exception as e:
                logger.error(f"Error on page {current_page}: {e}")
                self.errors.append(f"Page {current_page}: {str(e)}")
                break

        # Trim to max results if exceeded
        if len(all_listings) > max_results:
            all_listings = all_listings[:max_results]

        # Calculate market statistics
        self._calculate_market_stats(all_listings)

        logger.info(f"Listing extraction complete: {len(all_listings)} total listings")
        return all_listings

    def _build_search_url(self) -> str:
        """
        Build search URL with parameters.

        Returns:
            Complete search URL with query parameters
        """
        base_url = self.config['url']
        params = self.search_params

        # Build query string
        query_parts = []

        if 'zip' in params:
            query_parts.append(f"zip={params['zip']}")

        if 'min_price' in params:
            query_parts.append(f"min_price={params['min_price']}")

        if 'max_price' in params:
            query_parts.append(f"max_price={params['max_price']}")

        if 'radius' in params:
            query_parts.append(f"radius={params['radius']}")

        # Combine with base URL
        if query_parts:
            separator = '&' if '?' in base_url else '?'
            search_url = f"{base_url}{separator}{'&'.join(query_parts)}"
        else:
            search_url = base_url

        logger.info(f"Search URL: {search_url}")
        return search_url

    async def _extract_listings_from_page(self) -> List[Dict[str, Any]]:
        """
        Extract listing data from current page with safety limits.

        Returns:
            List of listing dicts from current page

        Safety features:
        - Limits extraction to 50 properties max per page
        - Checks if browser context is alive before each extraction
        - Gracefully handles extraction failures
        - Skips cards with missing critical data
        """
        listings = []
        selectors = self.config['selectors']

        # Find all listing cards
        listing_cards = await self.page.query_selector_all(selectors['listing_card'])

        # Try alternative selector if main one fails
        if not listing_cards:
            alt_selector = selectors.get('alt_listing_card')
            if alt_selector:
                listing_cards = await self.page.query_selector_all(alt_selector)

        total_cards = len(listing_cards)
        logger.info(f"Found {total_cards} listing cards on page")

        # Limit extraction to prevent browser crashes
        MAX_CARDS_PER_PAGE = 50
        cards_to_extract = min(total_cards, MAX_CARDS_PER_PAGE)

        if total_cards > MAX_CARDS_PER_PAGE:
            logger.info(f"Limiting extraction to {MAX_CARDS_PER_PAGE} cards (found {total_cards})")

        # Extract data from each card (up to limit)
        for idx in range(cards_to_extract):
            # Check if browser context is still alive
            try:
                if self.context.is_closed():
                    logger.warning(
                        f"Browser context closed at card {idx}/{cards_to_extract}. "
                        f"Extracted {len(listings)} listings before closure."
                    )
                    break
            except AttributeError:
                # context might not exist, skip check
                pass

            try:
                card = listing_cards[idx]
                listing_data = await self._extract_listing_from_card(card, idx)

                if listing_data and listing_data.get('address'):
                    listings.append(listing_data)
                else:
                    logger.warning(f"Skipping card {idx}: missing address")

            except Exception as e:
                # Log but continue - don't let one bad card stop entire scrape
                error_msg = str(e)
                if "Target page, context or browser has been closed" in error_msg:
                    logger.error(
                        f"Browser closed at card {idx}/{cards_to_extract}. "
                        f"Returning {len(listings)} extracted listings."
                    )
                    break
                else:
                    logger.warning(f"Failed to extract card {idx}: {e}")
                    # Don't add error cards to results - just skip them
                    continue

        logger.info(f"Successfully extracted {len(listings)} listings from {cards_to_extract} cards")
        return listings

    async def _safe_extract_text(
        self,
        card,
        selector: str,
        alt_selector: Optional[str] = None
    ) -> Optional[str]:
        """
        Safely extract text from element - returns None if not found.

        Args:
            card: Playwright element handle
            selector: CSS selector to try
            alt_selector: Alternative CSS selector (optional)

        Returns:
            Extracted text or None
        """
        try:
            elem = await card.query_selector(selector)
            if elem:
                text = await elem.text_content()
                return text.strip() if text else None

            # Try alternative selector if provided
            if alt_selector:
                elem = await card.query_selector(alt_selector)
                if elem:
                    text = await elem.text_content()
                    return text.strip() if text else None

        except Exception as e:
            logger.debug(f"Failed to extract with selector '{selector}': {e}")

        return None

    async def _extract_listing_from_card(
        self,
        card,
        card_index: int
    ) -> Dict[str, Any]:
        """
        Extract listing data from a single listing card.

        Only address and price are required - all other fields are optional.

        Args:
            card: Playwright element handle for listing card
            card_index: Index of card on page (for logging)

        Returns:
            Dict with listing data
        """
        selectors = self.config['selectors']
        data = {
            "card_index": card_index,
            "scraped_at": datetime.now().isoformat(),  # Fixed deprecation warning
        }

        # Extract REQUIRED fields: address and price
        address = await self._safe_extract_text(card, selectors['address'])
        if not address:
            logger.debug(f"Card {card_index}: No address found, skipping")
            return {}

        price = await self._safe_extract_text(
            card,
            selectors['price'],
            selectors.get('alt_price')
        )
        if not price:
            logger.debug(f"Card {card_index}: No price found, skipping")
            return {}

        data['address'] = address
        data['price'] = price

        # Extract BHK from title (e.g., "3 BHK Flat..." → 3)
        bhk_match = re.search(r'(\d+)\s*BHK', address, re.IGNORECASE)
        if bhk_match:
            data['bedrooms'] = int(bhk_match.group(1))

        # Extract sqft (convert from sqyrd if needed: 1 sqyrd = 9 sqft)
        sqft_text = await self._safe_extract_text(card, selectors.get('sqft', ''))
        if sqft_text:
            # Extract number from text like "307 sqyrd" or "2763 sqft"
            sqft_match = re.search(r'([\d,]+)', sqft_text.replace(',', ''))
            if sqft_match:
                sqft_value = float(sqft_match.group(1))
                # Convert sqyrd to sqft if needed
                if 'sqyrd' in sqft_text.lower() or 'sq yrd' in sqft_text.lower():
                    sqft_value = sqft_value * 9
                data['sqft'] = int(sqft_value)

        # Extract bathrooms
        bathrooms = await self._safe_extract_text(card, selectors.get('bathrooms', ''))
        if bathrooms:
            bath_match = re.search(r'(\d+)', bathrooms)
            if bath_match:
                data['bathrooms'] = int(bath_match.group(1))

        # Extract new fields (all optional)
        status = await self._safe_extract_text(card, selectors.get('status', ''))
        if status:
            data['status'] = status

        transaction = await self._safe_extract_text(card, selectors.get('transaction', ''))
        if transaction:
            data['transaction'] = transaction

        furnishing = await self._safe_extract_text(card, selectors.get('furnishing', ''))
        if furnishing:
            data['furnishing'] = furnishing

        society = await self._safe_extract_text(card, selectors.get('society', ''))
        if society:
            data['society'] = society

        parking = await self._safe_extract_text(card, selectors.get('parking', ''))
        if parking:
            data['parking'] = parking

        listing_date = await self._safe_extract_text(card, selectors.get('listing_date', ''))
        if listing_date:
            data['listing_date'] = listing_date

        agent_contact = await self._safe_extract_text(card, selectors.get('agent_contact', ''))
        if agent_contact:
            data['agent_contact'] = agent_contact

        # Try to get listing URL (link from card)
        try:
            link_elem = await card.query_selector('a[href]')
            if link_elem:
                href = await link_elem.get_attribute('href')
                if href:
                    # Make absolute URL
                    if not href.startswith('http'):
                        base_url = self.config['url'].split('?')[0].rsplit('/', 1)[0]
                        href = f"{base_url}/{href.lstrip('/')}"
                    data['listing_url'] = href
        except Exception as e:
            logger.debug(f"Could not extract listing URL: {e}")

        # Clean and validate data
        cleaned_data = clean_property_record(data)

        logger.debug(
            f"Extracted listing {card_index}: "
            f"{cleaned_data.get('address', 'N/A')[:50]}, "
            f"{cleaned_data.get('price', 'N/A')}"
        )

        return cleaned_data

    async def _navigate_to_next_page(self) -> bool:
        """
        Navigate to next page of results.

        Returns:
            True if successfully navigated, False if no more pages
        """
        pagination_config = self.config.get('pagination', {})
        pagination_type = pagination_config.get('type', 'button_click')
        selectors = self.config['selectors']

        try:
            if pagination_type == 'button_click':
                # Find and click next button
                next_button = await self.page.query_selector(selectors['next_button'])

                if not next_button:
                    logger.info("Next button not found - end of pagination")
                    return False

                # Check if button is disabled
                is_disabled = await next_button.get_attribute('disabled')
                aria_disabled = await next_button.get_attribute('aria-disabled')
                class_name = await next_button.get_attribute('class')

                if (is_disabled or
                    aria_disabled == 'true' or
                    (class_name and 'disabled' in class_name.lower())):
                    logger.info("Next button disabled - end of pagination")
                    return False

                # Click and wait for navigation
                logger.info("Clicking next page button...")
                await next_button.click()
                await self.page.wait_for_load_state('domcontentloaded')

                return True

            elif pagination_type == 'url_param':
                # Increment page parameter in URL
                current_url = self.page.url
                param_name = pagination_config.get('url_param_name', 'pg')

                # Extract current page number
                match = re.search(rf'{param_name}=(\d+)', current_url)
                if match:
                    current_page_num = int(match.group(1))
                    next_page_num = current_page_num + 1
                    next_url = re.sub(
                        rf'{param_name}=\d+',
                        f'{param_name}={next_page_num}',
                        current_url
                    )
                else:
                    # Add page parameter
                    separator = '&' if '?' in current_url else '?'
                    next_url = f"{current_url}{separator}{param_name}=2"

                logger.info(f"Navigating to: {next_url}")
                await self.page.goto(next_url)
                await self.page.wait_for_load_state('domcontentloaded')

                return True

            elif pagination_type == 'infinite_scroll':
                # Scroll to bottom to load more
                logger.info("Scrolling to load more results...")

                previous_height = await self.page.evaluate('document.body.scrollHeight')
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)  # Wait for content to load

                new_height = await self.page.evaluate('document.body.scrollHeight')

                if new_height > previous_height:
                    logger.info("More content loaded")
                    return True
                else:
                    logger.info("No more content to load")
                    return False

            else:
                logger.warning(f"Unknown pagination type: {pagination_type}")
                return False

        except Exception as e:
            logger.error(f"Failed to navigate to next page: {e}")
            return False

    def _calculate_market_stats(self, listings: List[Dict[str, Any]]) -> None:
        """
        Calculate market statistics from listings.

        Adds median price and price per sqft to metadata.

        Args:
            listings: List of listing records
        """
        try:
            # Extract valid prices
            prices = [
                listing['price']
                for listing in listings
                if listing.get('price') and isinstance(listing['price'], (int, float))
            ]

            # Extract price per sqft
            price_per_sqft_list = []
            for listing in listings:
                price = listing.get('price')
                sqft = listing.get('sqft')
                if price and sqft and isinstance(price, (int, float)) and isinstance(sqft, (int, float)) and sqft > 0:
                    price_per_sqft_list.append(price / sqft)

            # Calculate stats
            stats = {
                "total_listings": len(listings),
                "valid_prices": len(prices),
            }

            if prices:
                stats["median_price"] = statistics.median(prices)
                stats["mean_price"] = statistics.mean(prices)
                stats["min_price"] = min(prices)
                stats["max_price"] = max(prices)

            if price_per_sqft_list:
                stats["median_price_per_sqft"] = statistics.median(price_per_sqft_list)
                stats["mean_price_per_sqft"] = statistics.mean(price_per_sqft_list)

            logger.info(f"Market statistics: {stats}")

            # Store in instance for later use
            self.market_stats = stats

        except Exception as e:
            logger.warning(f"Failed to calculate market stats: {e}")
            self.market_stats = {}

    def get_comparables_for_property(
        self,
        target_property: Dict[str, Any],
        listings: List[Dict[str, Any]],
        max_distance_miles: float = 0.5,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find comparable properties for a target property.

        Args:
            target_property: Property to find comparables for
            listings: List of available listings
            max_distance_miles: Maximum distance for comparables
            max_results: Maximum number of comparables to return

        Returns:
            List of comparable properties sorted by relevance

        Note: This is a simple implementation. In production, you'd use
        actual geolocation distance calculations.
        """
        comparables = []

        target_price = target_property.get('price', 0)
        target_bedrooms = target_property.get('bedrooms', 0)
        target_sqft = target_property.get('sqft', 0)

        for listing in listings:
            # Skip if same property
            if listing.get('address') == target_property.get('address'):
                continue

            # Calculate similarity score (simple heuristic)
            score = 0

            # Price similarity (within 20%)
            listing_price = listing.get('price', 0)
            if target_price and listing_price:
                price_diff_pct = abs(listing_price - target_price) / target_price
                if price_diff_pct <= 0.2:
                    score += 3

            # Bedroom match
            if listing.get('bedrooms') == target_bedrooms:
                score += 2

            # Sqft similarity (within 20%)
            listing_sqft = listing.get('sqft', 0)
            if target_sqft and listing_sqft:
                sqft_diff_pct = abs(listing_sqft - target_sqft) / target_sqft
                if sqft_diff_pct <= 0.2:
                    score += 2

            if score > 0:
                listing_copy = listing.copy()
                listing_copy['_comparable_score'] = score
                comparables.append(listing_copy)

        # Sort by score and return top results
        comparables.sort(key=lambda x: x['_comparable_score'], reverse=True)

        return comparables[:max_results]
