import asyncio
import aiohttp
import random
from typing import List
from pydantic import BaseModel, HttpUrl, ValidationError


class APIResponse(BaseModel):
    url: HttpUrl
    status: int
    data: dict

print("Hello, World Test124453dsf!")


class ExternalAPIError(Exception):
    """Custom exception for API-related issues."""
    pass


async def fetch_with_retry(session: aiohttp.ClientSession, url: str, retries: int = 3) -> APIResponse:
    delay = 1
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url) as response:
                status = response.status
                data = await response.json()
                validated = APIResponse(url=url, status=status, data=data)
                return validated
        except (aiohttp.ClientError, asyncio.TimeoutError, ValidationError) as e:
            print(f"[Attempt {attempt}] Error fetching {url}: {e}")
            if attempt == retries:
                raise ExternalAPIError(f"Failed to fetch {url} after {retries} attempts.")
            await asyncio.sleep(delay)
            delay *= 2 + random.uniform(0, 1)  # Exponential backoff
    raise ExternalAPIError("Unreachable code reached.")


async def fetch_multiple_urls(urls: List[str]) -> List[APIResponse]:
    """
    Asynchronously fetches and validates data from multiple URLs.

    Args:
        urls (List[str]): List of API endpoint URLs.

    Returns:
        List[APIResponse]: List of validated API response objects.
    """
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_with_retry(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, APIResponse)]


# # Example usage
# if __name__ == "__main__":

#     responses = asyncio.run(fetch_multiple_urls(urls_to_fetch))
#     for res in responses:
#         print(f"\nURL: {res.url}\nStatus: {res.status}\nKeys: {list(res.data.keys())}")
