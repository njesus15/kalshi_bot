import asyncio
import aiohttp

HEALTHCHECK_URL = "https://hc-ping.com/d8e50ea4-9461-4520-91bd-a75df7e7562b"
PING_INTERVAL = 30  # seconds

async def heartbeat():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(HEALTHCHECK_URL, timeout=5) as resp:
                    await resp.text()  # we just want to ping
            except Exception as e:
                print("Heartbeat failed:", e)
            await asyncio.sleep(PING_INTERVAL)