import asyncio
from typing import Any
import httpx

from .config import settings


class AnakinClient:
    def __init__(self) -> None:
        self.base_url = settings.anakin_base_url
        self.api_key = settings.anakin_api_key

    @property
    def headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def search(self, prompt: str, limit: int = 5) -> dict[str, Any]:
        """Returns {"results": [...], "error": "..."}. Never raises."""
        if not self.api_key:
            return {"results": [], "error": "Missing ANAKIN_API_KEY"}
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                res = await client.post(
                    f"{self.base_url}/search",
                    headers=self.headers,
                    json={"prompt": prompt, "limit": limit},
                )
                if res.status_code >= 400:
                    try:
                        data = res.json()
                    except Exception:
                        return {"results": [], "error": f"HTTP {res.status_code}"}
                    raw_msg = str(data.get("message") or data.get("error") or f"HTTP {res.status_code}")
                    if res.status_code >= 500 or "search_error" in (data.get("error") or ""):
                        friendly = (
                            "Anakin search is temporarily unavailable (server error on Anakin's side). "
                            "Please retry in a minute. Status: " + raw_msg
                        )
                    elif "insufficient_credit" in raw_msg.lower() or "credit" in (data.get("error") or "").lower():
                        friendly = (
                            "Anakin account is out of search credits. Top up at https://anakin.io to continue."
                        )
                    else:
                        friendly = raw_msg
                    return {"results": [], "error": friendly[:240]}
                data = res.json()
                return {"results": data.get("results", []), "error": None}
        except Exception as e:
            return {"results": [], "error": str(e)[:200]}

    async def submit_scrape(
        self,
        client: httpx.AsyncClient,
        url: str,
        use_browser: bool = False,
        generate_json: bool = True,
    ) -> str | None:
        try:
            res = await client.post(
                f"{self.base_url}/url-scraper",
                headers=self.headers,
                json={
                    "url": url,
                    "country": settings.anakin_country,
                    "useBrowser": use_browser,
                    "generateJson": generate_json,
                },
            )
            res.raise_for_status()
            return res.json().get("jobId")
        except Exception:
            return None

    async def get_scrape_job(self, client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
        res = await client.get(f"{self.base_url}/url-scraper/{job_id}", headers=self.headers)
        res.raise_for_status()
        return res.json()

    async def poll_scrape_job(self, client: httpx.AsyncClient, job_id: str) -> dict[str, Any]:
        max_attempts = max(1, settings.poll_timeout_ms // settings.poll_interval_ms)
        for _ in range(max_attempts):
            try:
                data = await self.get_scrape_job(client, job_id)
            except Exception:
                await asyncio.sleep(settings.poll_interval_ms / 1000)
                continue
            status = data.get("status")
            if status in {"completed", "failed"}:
                return data
            await asyncio.sleep(settings.poll_interval_ms / 1000)
        return {"status": "failed", "error": "Polling timed out"}

    async def scrape_url(self, url: str, use_browser: bool = False) -> dict[str, Any]:
        if not self.api_key:
            return {}
        async with httpx.AsyncClient(timeout=60) as client:
            job_id = await self.submit_scrape(client, url, use_browser=use_browser)
            if not job_id:
                return {}
            return await self.poll_scrape_job(client, job_id)

    async def scrape_many(self, urls: list[str], use_browser: bool = False, concurrency: int = 5) -> list[dict[str, Any]]:
        if not self.api_key or not urls:
            return []
        sem = asyncio.Semaphore(concurrency)

        async def one(url: str) -> dict[str, Any]:
            async with sem:
                async with httpx.AsyncClient(timeout=60) as client:
                    job_id = await self.submit_scrape(client, url, use_browser=use_browser)
                    if not job_id:
                        return {"url": url, "status": "failed"}
                    data = await self.poll_scrape_job(client, job_id)
                    data.setdefault("url", url)
                    return data

        return await asyncio.gather(*(one(u) for u in urls))
