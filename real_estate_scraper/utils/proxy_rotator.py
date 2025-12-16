"""
Proxy rotation and user-agent management for anti-bot detection.

This module handles:
- Rotating through a pool of proxies
- Tracking failed proxies and removing them after threshold
- Generating realistic user-agents
- Providing randomized browser headers and viewport sizes
"""

import random
from typing import Optional, Dict, List
from collections import defaultdict

from config.settings import (
    PROXY_LIST,
    PROXY_FAILURE_THRESHOLD,
    USER_AGENT_POOL,
    VIEWPORT_SIZES,
    EXTRA_HTTP_HEADERS,
    DEFAULT_GEOLOCATION,
    TIMEZONE_ID,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ProxyRotator:
    """
    Manages proxy rotation with failure tracking and automatic removal.

    Attributes:
        proxies: List of available proxy URLs
        proxy_index: Current index in proxy rotation
        failure_counts: Dict tracking consecutive failures per proxy
        removed_proxies: Set of proxies removed due to excessive failures
    """

    def __init__(self, proxy_list: Optional[List[str]] = None):
        """
        Initialize proxy rotator.

        Args:
            proxy_list: Optional list of proxy URLs (defaults to settings.PROXY_LIST)
        """
        self.proxies = proxy_list if proxy_list is not None else PROXY_LIST.copy()
        self.proxy_index = 0
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.removed_proxies: set = set()

        if not self.proxies:
            logger.warning(
                "No proxies configured. Running in direct connection mode. "
                "This may lead to rate limiting or IP blocks."
            )

    def get_next_proxy(self) -> Optional[str]:
        """
        Get the next proxy in rotation.

        Returns:
            Proxy URL string or None if no proxies available

        Example:
            >>> rotator = ProxyRotator()
            >>> proxy = rotator.get_next_proxy()
            >>> # Use proxy in request
        """
        if not self.proxies:
            return None

        # Round-robin rotation
        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)

        return proxy

    def mark_proxy_failed(self, proxy: str) -> None:
        """
        Mark a proxy as failed and remove if threshold exceeded.

        Args:
            proxy: Proxy URL that failed

        Example:
            >>> rotator = ProxyRotator()
            >>> proxy = rotator.get_next_proxy()
            >>> # ... request fails ...
            >>> rotator.mark_proxy_failed(proxy)
        """
        if not proxy or proxy in self.removed_proxies:
            return

        self.failure_counts[proxy] += 1
        logger.warning(
            f"Proxy failed ({self.failure_counts[proxy]}/{PROXY_FAILURE_THRESHOLD}): "
            f"{self._mask_proxy_credentials(proxy)}"
        )

        # Remove proxy if threshold exceeded
        if self.failure_counts[proxy] >= PROXY_FAILURE_THRESHOLD:
            self._remove_proxy(proxy)

    def mark_proxy_success(self, proxy: str) -> None:
        """
        Reset failure count for a successful proxy.

        Args:
            proxy: Proxy URL that succeeded
        """
        if proxy and proxy in self.failure_counts:
            self.failure_counts[proxy] = 0
            logger.debug(f"Proxy succeeded, reset failure count: {self._mask_proxy_credentials(proxy)}")

    def _remove_proxy(self, proxy: str) -> None:
        """
        Remove a proxy from the rotation pool.

        Args:
            proxy: Proxy URL to remove
        """
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            self.removed_proxies.add(proxy)
            logger.error(
                f"Proxy removed from pool after {PROXY_FAILURE_THRESHOLD} failures: "
                f"{self._mask_proxy_credentials(proxy)}. "
                f"Remaining proxies: {len(self.proxies)}"
            )

            # Adjust index if needed
            if self.proxy_index >= len(self.proxies) and self.proxies:
                self.proxy_index = 0

            # Warn if running low on proxies
            if len(self.proxies) <= 2:
                logger.warning(
                    f"Low proxy count: {len(self.proxies)} remaining. "
                    "Consider adding more proxies to avoid rate limiting."
                )

    @staticmethod
    def _mask_proxy_credentials(proxy: str) -> str:
        """
        Mask credentials in proxy URL for logging.

        Args:
            proxy: Full proxy URL with credentials

        Returns:
            Proxy URL with masked credentials

        Example:
            >>> ProxyRotator._mask_proxy_credentials("http://user:pass@proxy.com:8080")
            'http://****:****@proxy.com:8080'
        """
        if '@' in proxy:
            protocol, rest = proxy.split('://', 1)
            creds, host = rest.split('@', 1)
            return f"{protocol}://****:****@{host}"
        return proxy

    def get_random_user_agent(self) -> str:
        """
        Get a random user-agent from the pool.

        Returns:
            User-agent string

        Example:
            >>> rotator = ProxyRotator()
            >>> ua = rotator.get_random_user_agent()
            >>> # Use in browser context
        """
        return random.choice(USER_AGENT_POOL)

    def get_random_viewport(self) -> Dict[str, int]:
        """
        Get a random viewport size.

        Returns:
            Dict with width and height

        Example:
            >>> rotator = ProxyRotator()
            >>> viewport = rotator.get_random_viewport()
            >>> # {"width": 1920, "height": 1080}
        """
        return random.choice(VIEWPORT_SIZES).copy()

    def get_browser_context_config(self) -> Dict:
        """
        Get complete browser context configuration with anti-detection settings.

        Returns:
            Dict with proxy, user_agent, viewport, headers, geolocation, timezone

        Example:
            >>> rotator = ProxyRotator()
            >>> config = rotator.get_browser_context_config()
            >>> # Use in playwright browser.new_context(**config)
        """
        config = {
            "user_agent": self.get_random_user_agent(),
            "viewport": self.get_random_viewport(),
            "extra_http_headers": EXTRA_HTTP_HEADERS.copy(),
            "geolocation": DEFAULT_GEOLOCATION.copy(),
            "permissions": ["geolocation"],
            "timezone_id": TIMEZONE_ID,
            "locale": "en-US",
            "color_scheme": random.choice(["light", "dark"]),
        }

        # Add proxy if available
        proxy = self.get_next_proxy()
        if proxy:
            config["proxy"] = {"server": proxy}
            logger.debug(f"Using proxy: {self._mask_proxy_credentials(proxy)}")

        return config

    def has_proxies(self) -> bool:
        """
        Check if there are any proxies available.

        Returns:
            True if proxies available, False otherwise
        """
        return len(self.proxies) > 0

    def get_stats(self) -> Dict:
        """
        Get statistics about proxy usage.

        Returns:
            Dict with proxy stats (total, active, removed, failures)
        """
        return {
            "total_configured": len(PROXY_LIST),
            "active_proxies": len(self.proxies),
            "removed_proxies": len(self.removed_proxies),
            "failure_counts": dict(self.failure_counts),
        }


# Global singleton instance for easy import
_global_rotator = None


def get_rotator() -> ProxyRotator:
    """
    Get or create the global ProxyRotator instance.

    Returns:
        Global ProxyRotator singleton

    Example:
        >>> from utils.proxy_rotator import get_rotator
        >>> rotator = get_rotator()
        >>> config = rotator.get_browser_context_config()
    """
    global _global_rotator
    if _global_rotator is None:
        _global_rotator = ProxyRotator()
    return _global_rotator
