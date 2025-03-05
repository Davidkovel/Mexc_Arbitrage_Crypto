import asyncio
import time

import aiohttp
from abc import abstractmethod, ABC

from utils.logger import *


class ExchangeApi(ABC):
    def __init__(self):
        self.session = None

    async def init(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    @abstractmethod
    async def get_price_coin(self, coin: str, address_contract: str, chain: str):
        pass


class PriceChecker(ABC):
    @abstractmethod
    async def check_pump(self, tokens: dict) -> bool:
        pass


class MexcAPI(ExchangeApi, PriceChecker):
    def __init__(self):
        super().__init__()
        self.base_url = "https://contract.mexc.com/api/v1/contract/fair_price/"
        self.price_history = {}

    async def close_session(self):
        await self.session.close()

    async def get_price_coin(self, coin: str, address_contract=None, chain=None, retries=3) -> dict:
        try:
            symbol = f"{coin}_USDT" if not coin.endswith("_USDT") else coin
            url = f"{self.base_url}{symbol}"
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {"error": f"HTTP error {response.status}"}

                response_data = await response.json()
                if not response_data.get("success", True):
                    if retries > 0:
                        await asyncio.sleep(2 ** (3 - retries))
                        return await self.get_price_coin(coin, address_contract, chain, retries - 1)
                    return {"error": response_data.get("message") + url}

                price = float(response_data["data"]["fairPrice"])
                return {"price": price}
        except Exception as ex:
            logger.error(f"Mexc exception: {ex}")
            return {"error": str(ex)}

    async def check_pump(self, tokens: dict) -> bool:
        try:
            for token, threshold in tokens.items():
                price_data = await self.get_price_coin(token)
                if "error" in price_data:
                    logger.error(f"Error while getting price for {token}: {price_data['error']}")
                    continue

                price = price_data["price"]
                prev_price, timestamp = self.price_history.get(token, (None, None))
                current_time = time.time()

                if prev_price and (current_time - timestamp) <= 15:
                    percent_change = ((price - prev_price) / prev_price) * 100
                    # print(f"{token} - {price} - {prev_price} - {percent_change}")
                    if percent_change > threshold:
                        print(
                            f"Pump detected for {token}: price increased by {percent_change:.2f}% in {current_time - timestamp:.2f} seconds")
                        return True

                self.price_history[token] = (price, current_time)

            return False
        except Exception as ex:
            logger.error(f"Error while checking pump - {ex}")
            return False

class PumpObs:
    def __init__(self, price_checker: PriceChecker, tokens: dict):
        self.price_checker = price_checker
        self.tokens = tokens

    async def start_pump(self):
        await self.price_checker.init()
        try:
            while True:
                await self.price_checker.check_pump(self.tokens)
                await asyncio.sleep(1)
        finally:
            await self.price_checker.close()


if __name__ == "__main__":
    mexc_exchange = MexcAPI()
    tokens = {"ONON": 7, "STONKS": 3, "CLAY": 2.50, "ALON": 2, "DHN": 2.50, "AKUMA": 5}
    obs = PumpObs(mexc_exchange, tokens)
    asyncio.run(obs.start_pump())
# 22:49: 3,33 - 22:50: 6,48 ||
