import time
from abc import ABC, abstractmethod

import asyncio
from collections import deque

import aiohttp

from random import uniform


class ExchangeApi(ABC):
    def __init__(self):
        self.session = None

    async def init(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    @abstractmethod
    async def get_account(self):
        pass

    @abstractmethod
    async def get_price_coin(self, coin: str, address_contract: str, chain: str):
        pass


class RateLimiter:
    def __init__(self, rate_limit: int, period: float):
        self.rate_limit = rate_limit
        self.period = period
        self.timestamps = deque()
        self.semaphore = asyncio.Semaphore(rate_limit)

    async def wait_for_capacity(self):
        now = time.monotonic()

        # Удаляем старые таймстампы
        while self.timestamps and now - self.timestamps[0] >= self.period:
            self.timestamps.popleft()

        if len(self.timestamps) >= self.rate_limit:
            sleep_time = self.period - (now - self.timestamps[0])
            await asyncio.sleep(sleep_time)
            return await self.wait_for_capacity()

        return True

    async def acquire(self):
        await self.semaphore.acquire()
        now = time.monotonic()
        self.timestamps.append(now)

    def release(self):
        self.semaphore.release()

class MexcAPI(ExchangeApi):
    def __init__(self):
        super().__init__()
        self.base_url = "https://contract.mexc.com/api/v1/contract/fair_price/"
        self.rate_limiter = RateLimiter(rate_limit=20, period=2)  # 20 запросов/2 секунды


    async def get_price_coin(self, coin: str, address_contract=None, chain=None, retries=3) -> dict:
        try:
            await self.rate_limiter.acquire()

            try:
                pair = "_USDT"
                coin += pair
                url = f"{self.base_url}{coin}"
                async with self.session.get(url) as response:
                    if response.status != 200:
                        print(f"[ERROR] Mexc HTTP error {response.status}")
                        return {"error": "HTTP error"}

                    response_data = await response.json()
                    if not response_data.get("success", True):
                        if retries > 0:
                            await asyncio.sleep(2 ** (3 - retries))
                            return await self.get_price_coin(coin, address_contract, chain, retries - 1)
                        return {"error": response_data.get("message")}

                    price = response_data["data"]["fairPrice"]
                    print('mexc', price)
                    return {"price": float(price)}
            finally:
                self.rate_limiter.release()

        except Exception as ex:
            print(f"[ERROR] Mexc exception: {ex}")
            return {"error": str(ex)}

    async def get_account(self):
        return {"account": "account info"}

    async def close_session(self):
        await self.session.close()

# экспозиональна backoff задержка

class DexApi(ExchangeApi):
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.dexscreener.com/token-pairs/v1/"
        self.rate_limiter = RateLimiter(rate_limit=5, period=1)  # 5 запросов в секунду
        self.retry_delay = 1  # Начальная задержка для retry
        self.max_retries = 3  # Максимальное количество попыток

    async def init(self):
        await super().init()

    async def get_price_coin(self, coin: str, address_contract: str, chain: str, retry_count=0) -> dict:
        try:
            await self.rate_limiter.acquire()

            try:
                url = f"{self.base_url}/{chain}/{address_contract}"
                async with self.session.get(url) as response:
                    if response.status == 429:  # Too Many Requests
                        if retry_count < self.max_retries:
                            # Экспоненциальная backoff-задержка
                            delay = self.retry_delay * (2 ** retry_count) + uniform(0, 1)
                            print(f"[WARNING] Dex rate limit exceeded. Retrying in {delay:.2f} seconds...")
                            await asyncio.sleep(delay)
                            return await self.get_price_coin(coin, address_contract, chain, retry_count + 1)
                        else:
                            print(f"[ERROR] Dex rate limit exceeded after {self.max_retries} retries")
                            return {"error": "Rate limit exceeded"}

                    if response.status != 200:
                        print(f"[ERROR] Dex HTTP error {response.status}")
                        return {"error": "HTTP error"}

                    response_data = await response.json()
                    price_usd = response_data[0]["priceUsd"]
                    print('dex', price_usd)
                    return {"price": float(price_usd)}
            finally:
                self.rate_limiter.release()

        except Exception as ex:
            print(f"[ERROR] Dex exception: {ex} - {coin}")
            return {"error": str(ex)}


    async def get_account(self):
        return {"account": "account info"}

    async def close_session(self):
        await self.session.close()
