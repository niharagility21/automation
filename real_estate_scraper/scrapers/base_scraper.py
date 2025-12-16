"""
Base scraper class with retry logic and anti-bot detection handling.

This abstract class provides:
- Async Playwright integration
- Exponential backoff retry logic (3 attempts: 5s, 10s, 20s)
- Proxy rotation on each retry
- User-agent randomization
- Anti-detection headers
- Comprehensive logging
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout

from config.settings import (
    MAX_RETRIES,
    RETRY_DELAYS,
    BROWSER_TIMEOUT,
    HEADLESS_MODE,
    REQUEST_DELAY_SECONDS,
)
from utils.proxy_rotator import get_rotator
from utils.logger import setup_logger, log_retry_attempt, log_proxy_rotation
from utils.data_validator import DataValidator

logger = setup_logger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.

    Provides retry logic, proxy rotation, and browser management.
    Subclasses must implement extract_data() method.

    Attributes:
        name: Scraper name
        config: Site-specific configuration
        browser: Playwright browser instance
        context: Browser context with anti-detection settings
        page: Current page
        proxy_rotator: Proxy rotation manager
        data_validator: Data validation utility
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize base scraper.

        Args:
            name: Scraper name (for logging)
            config: Site-specific configuration dict
        """
        self.name = name
        self.config = config
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.proxy_rotator = get_rotator()
        self.data_validator = DataValidator()
        self.start_time: Optional[datetime] = None
        self.records_extracted: List[Dict] = []
        self.errors: List[str] = []

        logger.info(f"Initialized {self.name} scraper")

    async def initialize_browser(self) -> None:
        """
        Initialize Playwright browser with anti-detection settings.

        Creates browser instance and context with:
        - Randomized user-agent
        - Randomized viewport
        - Proxy (if available)
        - Anti-detection headers
        """
        playwright = await async_playwright().start()

        # Launch browser (not headless for demo purposes)
        self.browser = await playwright.chromium.launch(
            headless=HEADLESS_MODE,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        # Get browser context config with proxy and anti-detection
        context_config = self.proxy_rotator.get_browser_context_config()

        # Create context
        self.context = await self.browser.new_context(**context_config)

        # Add anti-detection scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

        # Create initial page
        self.page = await self.context.new_page()

        # Set default timeout
        self.page.set_default_timeout(BROWSER_TIMEOUT)

        logger.info(
            f"Browser initialized: headless={HEADLESS_MODE}, "
            f"viewport={context_config['viewport']}, "
            f"user_agent={context_config['user_agent'][:50]}..."
        )

    async def close_browser(self) -> None:
        """Close browser and cleanup resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

        logger.info("Browser closed")

    async def _fetch_with_retry(
        self,
        url: str,
        max_retries: Optional[int] = None,
        wait_for_selector: Optional[str] = None
    ) -> Page:
        """
        Fetch URL with exponential backoff retry logic.

        This is the core retry mechanism:
        - Attempt 1: 5s delay on failure
        - Attempt 2: 10s delay on failure
        - Attempt 3: 20s delay on failure
        - Rotates proxy + user-agent on each retry

        Args:
            url: URL to fetch
            max_retries: Maximum retry attempts (default: settings.MAX_RETRIES)
            wait_for_selector: CSS selector to wait for after page load

        Returns:
            Page object if successful

        Raises:
            Exception: If all retries exhausted

        Example:
            >>> scraper = AuctionScraper(config)
            >>> page = await scraper._fetch_with_retry("https://example.com")
        """
        retries = max_retries if max_retries is not None else MAX_RETRIES
        last_error = None

        for attempt in range(1, retries + 1):
            current_proxy = None

            try:
                logger.info(f"[Attempt {attempt}/{retries}] Fetching: {url}")

                # Navigate to URL
                response = await self.page.goto(url, wait_until="domcontentloaded")

                # Check for blocking status codes
                if response and response.status in [403, 429, 503]:
                    raise Exception(
                        f"Blocked response: {response.status} {response.status_text}"
                    )

                # Wait for selector if specified
                if wait_for_selector:
                    try:
                        await self.page.wait_for_selector(
                            wait_for_selector,
                            timeout=BROWSER_TIMEOUT
                        )
                        logger.debug(f"Found selector: {wait_for_selector}")
                    except PlaywrightTimeout:
                        logger.warning(
                            f"Selector not found: {wait_for_selector}. "
                            "Continuing anyway..."
                        )

                # Success!
                logger.info(f"✓ Successfully fetched {url}")

                # Mark proxy as successful if used
                if current_proxy:
                    self.proxy_rotator.mark_proxy_success(current_proxy)

                return self.page

            except (PlaywrightTimeout, Exception) as e:
                last_error = e
                reason = f"{type(e).__name__}: {str(e)}"

                # Mark proxy as failed if used
                if current_proxy:
                    self.proxy_rotator.mark_proxy_failed(current_proxy)

                # Don't retry on last attempt
                if attempt >= retries:
                    logger.error(
                        f"✗ All retries exhausted for {url}. Last error: {reason}"
                    )
                    break

                # Get delay for this attempt
                delay = RETRY_DELAYS[attempt - 1] if attempt <= len(RETRY_DELAYS) else 20

                # Log retry attempt
                log_retry_attempt(
                    logger=logger,
                    url=url,
                    attempt=attempt,
                    max_retries=retries,
                    delay=delay,
                    reason=reason
                )

                # Wait before retry
                await asyncio.sleep(delay)

                # Rotate proxy and user-agent for next attempt
                await self._rotate_browser_config()

        # All retries failed
        error_msg = f"Failed to fetch {url} after {retries} attempts: {last_error}"
        logger.error(error_msg)
        self.errors.append(error_msg)
        raise Exception(error_msg)

    async def _rotate_browser_config(self) -> None:
        """
        Rotate browser configuration (proxy + user-agent).

        Creates a new browser context with fresh proxy and user-agent.
        Called automatically on retry attempts.
        """
        logger.info("Rotating browser configuration (proxy + user-agent)...")

        # Get old proxy for logging
        old_config = self.proxy_rotator.get_browser_context_config()
        old_proxy = old_config.get('proxy', {}).get('server')

        # Close current context
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()

        # Create new context with rotated settings
        new_config = self.proxy_rotator.get_browser_context_config()
        new_proxy = new_config.get('proxy', {}).get('server')

        self.context = await self.browser.new_context(**new_config)

        # Add anti-detection scripts again
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Create new page
        self.page = await self.context.new_page()
        self.page.set_default_timeout(BROWSER_TIMEOUT)

        # Log rotation
        log_proxy_rotation(
            logger=logger,
            old_proxy=old_proxy,
            new_proxy=new_proxy or "No proxy",
            reason="retry attempt"
        )

        logger.info(f"New user-agent: {new_config['user_agent'][:50]}...")

    async def download_file(self, url: str, save_path: Path) -> Optional[Path]:
        """
        Download a file (e.g., PDF) from URL.

        Args:
            url: File URL
            save_path: Path to save file

        Returns:
            Path to downloaded file or None if failed

        Example:
            >>> pdf_path = await scraper.download_file(
            ...     "https://example.com/appraisal.pdf",
            ...     Path("/tmp/appraisal.pdf")
            ... )
        """
        try:
            logger.info(f"Downloading file: {url}")

            # Navigate to URL and wait for download
            async with self.page.expect_download() as download_info:
                await self.page.goto(url)

            download = await download_info.value

            # Save to specified path
            await download.save_as(save_path)

            logger.info(f"✓ File downloaded: {save_path}")
            return save_path

        except Exception as e:
            logger.error(f"✗ Failed to download {url}: {e}")
            return None

    async def wait_politely(self, seconds: Optional[float] = None) -> None:
        """
        Wait between requests to avoid rate limiting.

        Args:
            seconds: Wait time (default: settings.REQUEST_DELAY_SECONDS)
        """
        delay = seconds if seconds is not None else REQUEST_DELAY_SECONDS
        logger.debug(f"Waiting {delay}s before next request...")
        await asyncio.sleep(delay)

    @abstractmethod
    async def extract_data(self) -> List[Dict[str, Any]]:
        """
        Extract data from target site (must be implemented by subclasses).

        Returns:
            List of extracted property records

        Example:
            >>> class MyGod(BaseScraper):
            ...     async def extract_data(self):
            ...         await self._fetch_with_retry(self.config['url'])
            ...         # Extract data from self.page
            ...         return [{"address": "123 Main St", "price": 450000}]
        """
        pass

    async def run(self) -> Dict[str, Any]:
        """
        Run the complete scraping process.

        Returns:
            Dict with scraped data and metadata

        Example:
            >>> scraper = AuctionScraper(config)
            >>> result = await scraper.run()
            >>> print(f"Extracted {result['total_records']} records")
        """
        self.start_time = datetime.now()
        logger.info(f"Starting {self.name} scraper...")

        try:
            # Initialize browser
            await self.initialize_browser()

            # Extract data (implemented by subclass)
            self.records_extracted = await self.extract_data()

            # Calculate stats
            successful = len([r for r in self.records_extracted if not r.get('error')])
            failed = len(self.records_extracted) - successful

            # Build result
            result = {
                "timestamp": datetime.now().isoformat(),
                "scraper_name": self.name,
                "scraper_type": self.config.get('name', 'unknown'),
                "total_records": len(self.records_extracted),
                "successful_records": successful,
                "failed_records": failed,
                "records": self.records_extracted,
                "errors": self.errors,
                "execution_time_seconds": (datetime.now() - self.start_time).total_seconds(),
                "proxy_stats": self.proxy_rotator.get_stats(),
            }

            logger.info(
                f"✓ {self.name} completed: {successful} successful, "
                f"{failed} failed, {len(self.errors)} errors"
            )

            return result

        except Exception as e:
            logger.error(f"✗ {self.name} failed: {e}", exc_info=True)
            self.errors.append(str(e))

            return {
                "timestamp": datetime.now().isoformat(),
                "scraper_name": self.name,
                "scraper_type": self.config.get('name', 'unknown'),
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "records": [],
                "errors": self.errors,
                "execution_time_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            }

        finally:
            # Cleanup
            await self.close_browser()
