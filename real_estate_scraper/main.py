#!/usr/bin/env python3
"""
Main entry point for the real estate scraper.

Usage:
    python main.py --site auction
    python main.py --site listing
    python main.py --site both

This script orchestrates the scraping process, runs the appropriate
scraper(s), validates data, and exports results to JSON.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.auction_scraper import AuctionScraper
from scrapers.listing_scraper import ListingScraper
from config.scrapers_config import AUCTION_CONFIG, LISTING_CONFIG, SCRAPER_CONFIGS
from config.settings import OUTPUT_DIR
from utils.logger import setup_logger, log_extraction_success, log_extraction_error
from models.property_data import ScraperResult

logger = setup_logger(__name__)


class RealEstateScraper:
    """
    Main orchestrator for real estate scraping operations.

    Coordinates multiple scrapers, validates results, and exports data.
    """

    def __init__(self):
        """Initialize scraper orchestrator."""
        self.results: Dict[str, Any] = {}
        logger.info("Real Estate Scraper initialized")

    async def run_auction_scraper(self) -> Dict[str, Any]:
        """
        Run auction site scraper.

        Returns:
            Scraper result dict with auction data
        """
        logger.info("=" * 80)
        logger.info("STARTING AUCTION SCRAPER")
        logger.info("=" * 80)

        start_time = datetime.now()

        try:
            scraper = AuctionScraper(config=AUCTION_CONFIG)
            result = await scraper.run()

            duration = (datetime.now() - start_time).total_seconds()

            log_extraction_success(
                logger=logger,
                scraper_name="AuctionScraper",
                records_count=result['total_records'],
                duration_seconds=duration
            )

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()

            log_extraction_error(
                logger=logger,
                scraper_name="AuctionScraper",
                error=e
            )

            return {
                "timestamp": datetime.now().isoformat(),
                "scraper_name": "AuctionScraper",
                "scraper_type": "auction",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "records": [],
                "errors": [str(e)],
                "execution_time_seconds": duration,
            }

    async def run_listing_scraper(self) -> Dict[str, Any]:
        """
        Run listing site scraper.

        Returns:
            Scraper result dict with listing data
        """
        logger.info("=" * 80)
        logger.info("STARTING LISTING SCRAPER")
        logger.info("=" * 80)

        start_time = datetime.now()

        try:
            scraper = ListingScraper(config=LISTING_CONFIG)
            result = await scraper.run()

            # Add market stats if available
            if hasattr(scraper, 'market_stats'):
                result['market_stats'] = scraper.market_stats

            duration = (datetime.now() - start_time).total_seconds()

            log_extraction_success(
                logger=logger,
                scraper_name="ListingScraper",
                records_count=result['total_records'],
                duration_seconds=duration
            )

            return result

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()

            log_extraction_error(
                logger=logger,
                scraper_name="ListingScraper",
                error=e
            )

            return {
                "timestamp": datetime.now().isoformat(),
                "scraper_name": "ListingScraper",
                "scraper_type": "listing",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "records": [],
                "errors": [str(e)],
                "execution_time_seconds": duration,
            }

    async def run_both_scrapers(self) -> Dict[str, Any]:
        """
        Run both auction and listing scrapers in sequence.

        Returns:
            Combined results dict
        """
        logger.info("Running both scrapers in sequence...")

        # Run auction scraper
        auction_result = await self.run_auction_scraper()

        # Run listing scraper
        listing_result = await self.run_listing_scraper()

        # Combine results
        combined_result = {
            "timestamp": datetime.now().isoformat(),
            "scrapers_run": ["auction", "listing"],
            "auction_scraper": auction_result,
            "listing_scraper": listing_result,
            "total_records": (
                auction_result['total_records'] +
                listing_result['total_records']
            ),
            "total_successful": (
                auction_result['successful_records'] +
                listing_result['successful_records']
            ),
            "total_failed": (
                auction_result['failed_records'] +
                listing_result['failed_records']
            ),
        }

        return combined_result

    def export_to_json(
        self,
        data: Dict[str, Any],
        scraper_type: str
    ) -> Path:
        """
        Export scraper results to JSON file.

        Args:
            data: Scraper result data
            scraper_type: Type of scraper (auction, listing, both)

        Returns:
            Path to exported JSON file
        """
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{scraper_type}_{timestamp}.json"
        output_path = OUTPUT_DIR / filename

        # Write JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Results exported to: {output_path}")
        logger.info(f"  Total records: {data.get('total_records', 0)}")

        return output_path

    def print_summary(self, result: Dict[str, Any]) -> None:
        """
        Print summary of scraping results.

        Args:
            result: Scraper result dict
        """
        print("\n" + "=" * 80)
        print("SCRAPING SUMMARY")
        print("=" * 80)

        if 'scrapers_run' in result:
            # Combined results
            print(f"Scrapers run: {', '.join(result['scrapers_run'])}")
            print(f"Total records: {result['total_records']}")
            print(f"Successful: {result['total_successful']}")
            print(f"Failed: {result['total_failed']}")

            print("\nAuction Scraper:")
            auction = result['auction_scraper']
            print(f"  Records: {auction['total_records']}")
            print(f"  Successful: {auction['successful_records']}")
            print(f"  Errors: {len(auction.get('errors', []))}")

            print("\nListing Scraper:")
            listing = result['listing_scraper']
            print(f"  Records: {listing['total_records']}")
            print(f"  Successful: {listing['successful_records']}")
            print(f"  Errors: {len(listing.get('errors', []))}")

        else:
            # Single scraper result
            print(f"Scraper: {result.get('scraper_name', 'Unknown')}")
            print(f"Type: {result.get('scraper_type', 'Unknown')}")
            print(f"Total records: {result['total_records']}")
            print(f"Successful: {result['successful_records']}")
            print(f"Failed: {result['failed_records']}")
            print(f"Execution time: {result.get('execution_time_seconds', 0):.2f}s")

            if result.get('errors'):
                print(f"\nErrors ({len(result['errors'])}):")
                for error in result['errors'][:5]:  # Show first 5 errors
                    print(f"  - {error}")

            # Show sample records
            if result.get('records'):
                print(f"\nSample records (first 3):")
                for i, record in enumerate(result['records'][:3], 1):
                    address = record.get('address', 'N/A')
                    price = record.get('price') or record.get('estimated_value')
                    price_str = f"${price:,.0f}" if price else "N/A"
                    print(f"  {i}. {address[:60]} - {price_str}")

        print("=" * 80 + "\n")


async def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Real Estate Scraper - Production-grade web scraping for real estate data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --site auction      # Run auction scraper only
  python main.py --site listing      # Run listing scraper only
  python main.py --site both         # Run both scrapers

The scraper will:
  1. Use anti-bot detection (proxy rotation, user-agent spoofing)
  2. Retry failed requests with exponential backoff (5s, 10s, 20s)
  3. Extract and validate property data
  4. Export results to JSON in the output/ directory
        """
    )

    parser.add_argument(
        '--site',
        type=str,
        choices=['auction', 'listing', 'both'],
        default='auction',
        help='Which scraper to run (default: auction)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Custom output file path (optional)'
    )

    args = parser.parse_args()

    # Initialize orchestrator
    scraper = RealEstateScraper()

    # Run appropriate scraper(s)
    logger.info(f"Starting scraper with mode: {args.site}")

    try:
        if args.site == 'auction':
            result = await scraper.run_auction_scraper()
        elif args.site == 'listing':
            result = await scraper.run_listing_scraper()
        elif args.site == 'both':
            result = await scraper.run_both_scrapers()
        else:
            logger.error(f"Invalid site: {args.site}")
            return 1

        # Export results
        output_path = scraper.export_to_json(result, args.site)

        # Print summary
        scraper.print_summary(result)

        logger.info("✓ Scraping complete!")
        return 0

    except KeyboardInterrupt:
        logger.warning("\n✗ Scraping interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"✗ Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    # Run async main
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
