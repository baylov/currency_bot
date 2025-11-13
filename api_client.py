import aiohttp
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class APIClient:
    """Base API client for making HTTP requests."""
    
    def __init__(self, base_url: str, proxy: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.proxy = proxy
        self.session: Optional[aiohttp.ClientSession] = None
    
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
            timeout = aiohttp.ClientTimeout(total=30)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )
    
    async def close_session(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request."""
        if not self.session:
            await self.start_session()
        
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        try:
            async with self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data,
                headers=headers,
            ) as response:
                response.raise_for_status()
                return await response.json()
        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            raise


class CoinGeckoClient(APIClient):
    """CoinGecko API client."""
    
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
        """Get simple price data from CoinGecko."""
        params = {
            "ids": ids,
            "vs_currencies": vs_currencies,
            "include_market_cap": str(include_market_cap).lower(),
            "include_24hr_vol": str(include_24hr_vol).lower(),
            "include_24hr_change": str(include_24hr_change).lower(),
            "include_last_updated_at": str(include_last_updated_at).lower(),
        }
        
        return await self.request("GET", "/simple/price", params=params)
    
    async def ping(self) -> Dict[str, Any]:
        """Check CoinGecko API status."""
        return await self.request("GET", "/ping")