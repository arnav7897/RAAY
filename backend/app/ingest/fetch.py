import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.ingest.models import FetchResult


class PoliteFetcher:
    def __init__(
        self,
        *,
        cache_dir: Path,
        user_agent: str,
        interval_seconds: float = 1.0,
        timeout_seconds: float = 30.0,
    ) -> None:
        if interval_seconds < 1.0:
            raise ValueError("RBI requests must be at least one second apart")
        self._cache_dir = cache_dir
        self._user_agent = user_agent
        self._interval_seconds = interval_seconds
        self._timeout = timeout_seconds
        self._last_request_at = 0.0
        self._robots: dict[str, RobotFileParser] = {}

    async def _throttle(self) -> None:
        loop = asyncio.get_running_loop()
        remaining = self._interval_seconds - (loop.time() - self._last_request_at)
        if remaining > 0:
            await asyncio.sleep(remaining)
        self._last_request_at = loop.time()

    async def _allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        policy = self._robots.get(origin)
        if policy is None:
            await self._throttle()
            response = await client.get(f"{origin}/robots.txt")
            policy = RobotFileParser()
            policy.set_url(f"{origin}/robots.txt")
            policy.parse(response.text.splitlines() if response.is_success else [])
            self._robots[origin] = policy
        return policy.can_fetch(self._user_agent, url)

    async def fetch(self, url: str) -> FetchResult:
        headers = {"User-Agent": self._user_agent, "Accept": "text/html,application/pdf"}
        async with httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=self._timeout,
        ) as client:
            if not await self._allowed(client, url):
                raise PermissionError(f"robots.txt disallows fetching {url}")
            await self._throttle()
            response = await client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "application/octet-stream")
        retrieved_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        suffix = ".pdf" if "pdf" in content_type.casefold() else ".html"
        cache_key = hashlib.sha256(response.content).hexdigest()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self._cache_dir / f"{cache_key}{suffix}"
        if not cache_path.exists():
            cache_path.write_bytes(response.content)
        return FetchResult(
            url=str(response.url),
            content=response.content,
            content_type=content_type,
            retrieved_at=retrieved_at,
            cache_path=str(cache_path),
        )
