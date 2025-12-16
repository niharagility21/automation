"""
Auction site scraper for foreclosure and auction properties.

Extracts:
- Property addresses
- Estimated values
- Auction dates
- PDF appraisal documents

Handles PDF download and parsing for appraisal values.
"""

import asyncio
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from scrapers.base_scraper import BaseScraper
from config.settings import PDF_DOWNLOAD_DIR
from utils.logger import setup_logger
from utils.pdf_parser import extract_appraisal_values
from utils.data_validator import clean_property_record

logger = setup_logger(__name__)


class AuctionScraper(BaseScraper):
    """
    Scraper for real estate auction sites.

    Inherits retry logic and browser management from BaseScraper.
    Implements auction-specific data extraction and PDF parsing.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize auction scraper.

        Args:
            config: Auction site configuration from scrapers_config.py
        """
        super().__init__(name="AuctionScraper", config=config)

    async def extract_data(self) -> List[Dict[str, Any]]:
        """
        Extract auction property data from target site.

        Returns:
            List of auction property records

        Process:
        1. Navigate to auction listings page
        2. Extract property cards
        3. Download and parse PDF appraisals
        4. Paginate through results
        5. Clean and validate data
        """
        all_properties = []
        current_page = 1
        max_pages = self.config.get('pagination', {}).get('max_pages', 5)

        logger.info(f"Starting auction data extraction from {self.config['url']}")

        while current_page <= max_pages:
            try:
                logger.info(f"Processing page {current_page}/{max_pages}")

                # Fetch page with retry logic
                await self._fetch_with_retry(
                    url=self.config['url'],
                    wait_for_selector=self.config['wait_for']['selector']
                )

                # Extract properties from current page
                properties = await self._extract_properties_from_page()
                all_properties.extend(properties)

                logger.info(
                    f"Extracted {len(properties)} properties from page {current_page} "
                    f"(Total: {len(all_properties)})"
                )

                # Try to navigate to next page
                has_next = await self._navigate_to_next_page()
                if not has_next:
                    logger.info("No more pages to process")
                    break

                current_page += 1

                # Be polite - wait between pages
                await self.wait_politely(2)

            except Exception as e:
                logger.error(f"Error on page {current_page}: {e}")
                self.errors.append(f"Page {current_page}: {str(e)}")
                break

        logger.info(f"Auction extraction complete: {len(all_properties)} total properties")
        return all_properties

    async def _extract_properties_from_page(self) -> List[Dict[str, Any]]:
        """
        Extract all property data from current page.

        Returns:
            List of property dicts from current page
        """
        properties = []
        selectors = self.config['selectors']

        # Find all property cards
        property_cards = await self.page.query_selector_all(selectors['property_card'])

        # Try alternative selector if main one fails
        if not property_cards:
            alt_selector = selectors.get('alt_property_card')
            if alt_selector:
                property_cards = await self.page.query_selector_all(alt_selector)

        logger.info(f"Found {len(property_cards)} property cards on page")

        # Extract data from each card
        for idx, card in enumerate(property_cards):
            try:
                property_data = await self._extract_property_from_card(card, idx)
                if property_data and property_data.get('address'):
                    properties.append(property_data)
                else:
                    logger.warning(f"Skipping card {idx}: missing address")

            except Exception as e:
                logger.warning(f"Failed to extract card {idx}: {e}")
                properties.append({
                    "error": str(e),
                    "card_index": idx,
                })

        return properties

    async def _extract_property_from_card(
        self,
        card,
        card_index: int
    ) -> Dict[str, Any]:
        """
        Extract property data from a single property card.

        Args:
            card: Playwright element handle for property card
            card_index: Index of card on page (for logging)

        Returns:
            Dict with property data
        """
        selectors = self.config['selectors']
        data = {
            "card_index": card_index,
            "scraped_at": datetime.now().isoformat(),
        }

        # Extract address
        address_elem = await card.query_selector(selectors['address'])
        if address_elem:
            data['address'] = await address_elem.text_content()

        # Extract price/estimated value
        price_elem = await card.query_selector(selectors['price'])
        if not price_elem:
            price_elem = await card.query_selector(selectors.get('alt_price', ''))

        if price_elem:
            data['price'] = await price_elem.text_content()

        # Extract auction date
        date_elem = await card.query_selector(selectors['auction_date'])
        if date_elem:
            data['auction_date'] = await date_elem.text_content()

        # Extract PDF link
        pdf_link_elem = await card.query_selector(selectors['pdf_link'])
        if pdf_link_elem:
            pdf_url = await pdf_link_elem.get_attribute('href')
            if pdf_url:
                # Make absolute URL if relative
                if not pdf_url.startswith('http'):
                    base_url = self.config['url'].rsplit('/', 1)[0]
                    pdf_url = f"{base_url}/{pdf_url.lstrip('/')}"

                data['pdf_url'] = pdf_url

                # Download and parse PDF
                pdf_data = await self._download_and_parse_pdf(pdf_url, card_index)
                if pdf_data:
                    data.update(pdf_data)

        # Clean and validate data
        cleaned_data = clean_property_record(data)

        logger.debug(
            f"Extracted property {card_index}: "
            f"{cleaned_data.get('address', 'N/A')[:50]}"
        )

        return cleaned_data

    async def _download_and_parse_pdf(
        self,
        pdf_url: str,
        card_index: int
    ) -> Optional[Dict[str, Any]]:
        """
        Download PDF and extract appraisal values.

        Args:
            pdf_url: URL to PDF document
            card_index: Index for unique filename

        Returns:
            Dict with extracted PDF data or None
        """
        try:
            logger.info(f"Downloading PDF from {pdf_url}")

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"auction_{card_index}_{timestamp}.pdf"
            pdf_path = PDF_DOWNLOAD_DIR / pdf_filename

            # Download PDF
            downloaded_path = await self.download_file(pdf_url, pdf_path)

            if not downloaded_path or not downloaded_path.exists():
                logger.warning(f"Failed to download PDF: {pdf_url}")
                return None

            # Parse PDF for appraisal values
            logger.info(f"Parsing PDF: {pdf_path.name}")
            pdf_data = await extract_appraisal_values(pdf_path)

            # Format for auction record
            result = {
                "estimated_value": pdf_data.get('estimated_value'),
                "appraisal_source": "pdf",
                "pdf_path": str(pdf_path),
                "confidence_score": pdf_data.get('confidence_score', 0.0),
            }

            # Merge property details if found in PDF
            if pdf_data.get('property_details'):
                details = pdf_data['property_details']
                for key, value in details.items():
                    if key not in result and value is not None:
                        result[key] = value

            logger.info(
                f"✓ PDF parsed: estimated_value={result['estimated_value']}, "
                f"confidence={result['confidence_score']:.2f}"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_url}: {e}")
            return {
                "appraisal_source": "pdf",
                "pdf_error": str(e),
            }

    async def _navigate_to_next_page(self) -> bool:
        """
        Navigate to next page of results.

        Returns:
            True if successfully navigated, False if no more pages

        Handles different pagination types:
        - button_click: Click "Next" button
        - url_param: Increment page parameter in URL
        - infinite_scroll: Scroll to load more
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

                if is_disabled or aria_disabled == 'true':
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
                param_name = pagination_config.get('url_param_name', 'page')

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
