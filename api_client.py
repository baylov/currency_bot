import asyncio
import aiohttp
from typing import Dict, Any, Optional, TypedDict
from urllib.parse import urljoin

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class PriceData(TypedDict):
    """Normalized price data structure."""
    btc: float
    eth: float
    usdt: float
    timestamp: Optional[int]
    currency: str


class APIError(Exception):
    """Base exception for API errors."""
    pass


class APITimeoutError(APIError):
    """Exception raised when API request times out."""
    pass


class APIRateLimitError(APIError):
    """Exception raised when API rate limit is exceeded."""
    pass


class APIClient:
    """Base API client for making HTTP requests with retry logic."""
    
    def __init__(self, base_url: str, proxy: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.proxy = proxy
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_retries = settings.api_max_retries
        self.retry_delay = settings.api_retry_delay
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_session()
    
    async def start_session(self) -> None:
        """Start the aiohttp session."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=settings.api_timeout)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )
            logger.debug("API client session started")
    
    async def close_session(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.debug("API client session closed")
    
    async def request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic and exponential backoff."""
        if not self.session:
            await self.start_session()
        
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        try:
            logger.debug(f"Making {method} request to {url} (attempt {retry_count + 1}/{self.max_retries + 1})")
            
            async with self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data,
                headers=headers,
                proxy=self.proxy,
            ) as response:
                # Check for rate limiting
                if response.status == 429:
                    logger.warning(f"Rate limit hit for {url}")
                    raise APIRateLimitError("API rate limit exceeded")
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                result = await response.json()
                logger.debug(f"Request to {url} succeeded")
                return result
        
        except asyncio.TimeoutError as e:
            logger.error(f"Request to {url} timed out (attempt {retry_count + 1}): {e}")
            if retry_count < self.max_retries:
                return await self._retry_request(
                    method, endpoint, params, data, headers, retry_count
                )
            raise APITimeoutError(f"Request timed out after {self.max_retries + 1} attempts")
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error for {url} (attempt {retry_count + 1}): {e}")
            if retry_count < self.max_retries:
                return await self._retry_request(
                    method, endpoint, params, data, headers, retry_count
                )
            raise APIError(f"Request failed after {self.max_retries + 1} attempts: {e}")
        
        except APIRateLimitError:
            logger.warning(f"Rate limit exceeded for {url}, retrying with backoff")
            if retry_count < self.max_retries:
                # Use longer delay for rate limiting
                return await self._retry_request(
                    method, endpoint, params, data, headers, retry_count, multiplier=2.0
                )
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error in API request to {url}: {e}", exc_info=True)
            raise APIError(f"Unexpected error: {e}")
    
    async def _retry_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]],
        data: Optional[Dict[str, Any]],
        headers: Optional[Dict[str, str]],
        retry_count: int,
        multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """Retry request with exponential backoff."""
        retry_count += 1
        # Exponential backoff: delay * 2^retry_count * multiplier
        delay = self.retry_delay * (2 ** retry_count) * multiplier
        logger.info(f"Retrying request in {delay:.2f} seconds (attempt {retry_count + 1}/{self.max_retries + 1})")
        await asyncio.sleep(delay)
        
        return await self.request(
            method=method,
            endpoint=endpoint,
            params=params,
            data=data,
            headers=headers,
            retry_count=retry_count,
        )


class CoinGeckoClient(APIClient):
    """CoinGecko API client with specialized methods for cryptocurrency price data."""
    
    # CoinGecko coin IDs for the cryptocurrencies we track
    COIN_IDS = {
        'btc': 'bitcoin',
        'eth': 'ethereum',
        'usdt': 'tether',
    }
    
    def __init__(self):
        super().__init__(
            base_url=settings.coingecko_base_url,
            proxy=settings.proxy_url,
        )
    
    async def get_simple_price(
        self, 
        ids: str, 
        vs_currencies: str,
        include_market_cap: bool = False,
        include_24hr_vol: bool = False,
        include_24hr_change: bool = False,
        include_last_updated_at: bool = False,
    ) -> Dict[str, Any]:
        """Get simple price data from CoinGecko.
        
        Args:
            ids: Comma-separated list of coin IDs
            vs_currencies: Comma-separated list of vs_currencies (e.g., 'usd,rub')
            include_market_cap: Include market cap data
            include_24hr_vol: Include 24h volume data
            include_24hr_change: Include 24h change data
            include_last_updated_at: Include last updated timestamp
        
        Returns:
            Price data from CoinGecko API
        """
        params = {
            "ids": ids,
            "vs_currencies": vs_currencies,
            "include_market_cap": str(include_market_cap).lower(),
            "include_24hr_vol": str(include_24hr_vol).lower(),
            "include_24hr_change": str(include_24hr_change).lower(),
            "include_last_updated_at": str(include_last_updated_at).lower(),
        }
        
        logger.info(f"Fetching prices for {ids} in {vs_currencies}")
        return await self.request("GET", "/simple/price", params=params)
    
    async def get_rub_prices(self) -> PriceData:
        """Fetch current RUB prices for BTC, ETH, and USDT in a single request.
        
        This is the main interface method for handlers and scheduler to get
        normalized price data.
        
        Returns:
            PriceData dictionary with btc, eth, usdt prices in RUB, timestamp, and currency
        
        Raises:
            APIError: If the request fails after all retries
        """
        try:
            # Fetch all three cryptocurrencies in a single request
            coin_ids = ','.join(self.COIN_IDS.values())
            
            logger.info("Fetching RUB prices for BTC, ETH, and USDT")
            
            raw_data = await self.get_simple_price(
                ids=coin_ids,
                vs_currencies='rub',
                include_last_updated_at=True,
            )
            
            # Normalize the response data
            prices: PriceData = {
                'btc': raw_data.get('bitcoin', {}).get('rub', 0.0),
                'eth': raw_data.get('ethereum', {}).get('rub', 0.0),
                'usdt': raw_data.get('tether', {}).get('rub', 0.0),
                'timestamp': raw_data.get('bitcoin', {}).get('last_updated_at'),
                'currency': 'RUB',
            }
            
            logger.info(
                f"Successfully fetched RUB prices: "
                f"BTC={prices['btc']:.2f}, "
                f"ETH={prices['eth']:.2f}, "
                f"USDT={prices['usdt']:.2f}"
            )
            
            return prices
        
        except Exception as e:
            logger.error(f"Failed to fetch RUB prices: {e}", exc_info=True)
            raise APIError(f"Failed to fetch RUB prices: {e}")
    
    async def ping(self) -> Dict[str, Any]:
        """Check CoinGecko API status.
        
        Returns:
            API status response
        """
        logger.debug("Pinging CoinGecko API")
        return await self.request("GET", "/ping")


# Convenience function for easy usage
async def get_crypto_prices() -> PriceData:
    """Convenience function to fetch cryptocurrency prices in RUB.
    
    This function manages the client lifecycle automatically using
    async context manager.
    
    Returns:
        PriceData with BTC, ETH, and USDT prices in RUB
    
    Example:
        prices = await get_crypto_prices()
        print(f"BTC: {prices['btc']} RUB")
    """
    async with CoinGeckoClient() as client:
        return await client.get_rub_prices()
