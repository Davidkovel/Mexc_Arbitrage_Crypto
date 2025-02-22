import time
from abc import ABC, abstractmethod

import asyncio
from collections import deque

import aiohttp

from random import uniform

from aiohttp import BasicAuth

from utils.logger import *



proxies = [
   # {"url": "http://XXX:XXX", "login": "XXXX", "password": "XXXXX"},
]


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


class MexcAPI(ExchangeApi):
    def __init__(self):
        super().__init__()
        self.base_url = "https://contract.mexc.com/api/v1/contract/fair_price/"

    async def get_price_coin(self, coin: str, address_contract=None, chain=None, retries=3) -> dict:
        try:
            symbol = f"{coin}_USDT" if not coin.endswith("_USDT") else coin
            url = f"{self.base_url}{symbol}"
            async with self.session.get(url) as response:
                if response.status != 200:
                    # logger.error(f"Mexc HTTP error {response.status}")
                    return {"error": f"HTTP error {response.status}"}

                response_data = await response.json()
                if not response_data.get("success", True):
                    if retries > 0:
                        await asyncio.sleep(2 ** (3 - retries))
                        return await self.get_price_coin(coin, address_contract, chain, retries - 1)
                    return {"error": response_data.get("message") + url}

                price = response_data["data"]["fairPrice"]
                # logger.info(f'mexc {coin} {price}')
                return {"price": float(price)}
        except Exception as ex:
            logger.error(f"Mexc exception: {ex}")
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
        self.retry_delay = 1  # Начальная задержка для retry
        self.max_retries = 3  # Максимальное количество попыток
        self.proxies = proxies
        self.current_proxy_index = 0

    async def init(self):
        await super().init()

    async def change_proxy(self):
        proxy_info = self.proxies[self.current_proxy_index]
        proxy_url = proxy_info["url"]
        proxy_auth = BasicAuth(proxy_info["login"], proxy_info["password"])

        logger.info(f"Using proxy: {proxy_url}")
        return proxy_url, proxy_auth

    async def get_price_coin(self, coin: str, address_contract: str, chain: str) -> dict:
        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                # Получаем текущий прокси и аутентификацию
                proxy_info = self.proxies[self.current_proxy_index]
                proxy_url = proxy_info["url"]
                proxy_auth = BasicAuth(proxy_info["login"], proxy_info["password"])

                # logger.info(f"Using proxy: {proxy_url}")

                url = f"{self.base_url}/{chain}/{address_contract}"
                async with self.session.get(url, proxy=proxy_url, proxy_auth=proxy_auth) as response:
                    if response.status == 429:  # Ошибка 429 (Too Many Requests)
                        if retry_count < self.max_retries:
                            # Меняем прокси только если это последняя попытка
                            if retry_count == self.max_retries - 1:
                                self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
                                logger.warning(
                                    f"Dex rate limit exceeded. Switching to proxy: {self.proxies[self.current_proxy_index]['url']}")

                            # Экспоненциальная backoff-задержка
                            delay = self.retry_delay * (2 ** retry_count) + uniform(0, 1)
                            logger.warning(f"Dex rate limit exceeded. Retrying in {delay:.2f} seconds...")
                            await asyncio.sleep(delay)
                            retry_count += 1
                            continue  # Повторяем запрос
                        else:
                            logger.error(f"Dex rate limit exceeded after {self.max_retries} retries")
                            return {"error": "Rate limit exceeded"}

                    if response.status != 200:
                        logger.error(f"Dex HTTP error {response.status}")
                        return {"error": "HTTP error"}

                    response_data = await response.json()
                    price_usd = response_data[0]["priceUsd"]
                    # logger.info(f'dex: {coin} - {price_usd}')
                    return {"price": float(price_usd)}

            except Exception as ex:
                logger.error(f"Dex exception: {ex} - {coin}")
                return {"error": str(ex)}

        logger.error(f"Failed to fetch price for {coin} after {self.max_retries} retries")
        return {"error": "Max retries exceeded"}

    async def get_account(self):
        return {"account": "account info"}

    async def close_session(self):
        await self.session.close()



# УДАЛИТЬ КЛАСС RATE LIMIT ТАК КАК ОН ОСТАНАВЛИВАЕТ САМ ПРОЦЕСС КОДА!!
# class RateLimiter:




# class RateLimiter:
#     def __init__(self, rate_limit: int, period: float):
#         self.rate_limit = rate_limit
#         self.period = period
#         self.timestamps = deque()
#         self.semaphore = asyncio.Semaphore(rate_limit)
#
#     async def wait_for_capacity(self):
#         now = time.monotonic()
#
#         # Удаляем старые таймстампы
#         while self.timestamps and now - self.timestamps[0] >= self.period:
#             self.timestamps.popleft()
#
#         if len(self.timestamps) >= self.rate_limit:
#             sleep_time = self.period - (now - self.timestamps[0])
#             await asyncio.sleep(sleep_time)
#             return await self.wait_for_capacity()
#
#         return True
#
#     async def acquire(self):
#         await self.semaphore.acquire()
#         now = time.monotonic()
#         self.timestamps.append(now)
#
#     def release(self):
#         self.semaphore.release()
