import aiohttp
import asyncio
from typing import List

class SubscriptionFetcher:
    def __init__(self, fallback_list: List[str], timeout: int = 10):
        self.fallback_list = fallback_list
        self.timeout = timeout
        self.valid_mirror = None

    async def test_mirror(self, mirror: str) -> bool:
        try:
            test_url = f"{mirror}https://raw.githubusercontent.com/gfwlist/gfwlist/master/gfwlist.txt"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
                async with session.get(test_url) as resp:
                    return resp.status == 200
        except:
            return False

    async def get_valid_mirror(self) -> str:
        if self.valid_mirror:
            return self.valid_mirror

        print("\n[自救] 自动测试可用镜像...")
        tasks = []
        for proxy in self.fallback_list:
            if proxy.strip():
                tasks.append(self.test_mirror(proxy.strip()))
        
        results = await asyncio.gather(*tasks)
        for ok, mirror in zip(results, self.fallback_list):
            if ok:
                self.valid_mirror = mirror.strip()
                print(f"[自救] ✅ 可用镜像：{self.valid_mirror}")
                return self.valid_mirror

        print("[自救] ❌ 无可用镜像，将尝试直连")
        return None

    async def fetch_single(self, url: str, mirror: str):
        target = f"{mirror}{url}" if mirror else url
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(target) as resp:
                    if resp.status == 200:
                        return {
                            "source_url": url,
                            "target_url": target,
                            "ok": True,
                            "status": resp.status,
                            "error": "",
                            "content": await resp.text(),
                        }
                    return {
                        "source_url": url,
                        "target_url": target,
                        "ok": False,
                        "status": resp.status,
                        "error": f"HTTP {resp.status}",
                        "content": "",
                    }
        except Exception as e:
            return {
                "source_url": url,
                "target_url": target,
                "ok": False,
                "status": 0,
                "error": f"{type(e).__name__}: {e}",
                "content": "",
            }

    # ======================
    # 【多线程并发拉取】
    # ======================
    async def fetch_all(self, url_list: List[str]):
        mirror = await self.get_valid_mirror()
        tasks = [self.fetch_single(url, mirror) for url in url_list]
        return await asyncio.gather(*tasks)