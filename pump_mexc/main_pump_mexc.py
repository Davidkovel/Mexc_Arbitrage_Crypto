import asyncio
import time
from typing import Callable, Dict

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
    async def check_pump(self, tokens: dict, tg_notify) -> bool:
        pass


class MexcAPI(ExchangeApi, PriceChecker):
    def __init__(self):
        super().__init__()
        self.base_url = "https://contract.mexc.com/api/v1/contract/fair_price/"
        self.price_history = {}
        self.semaphore = asyncio.Semaphore(5)
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

    async def check_pump(self, tokens: Dict[str, float], tg_notify: 'TgNotify') -> bool:
        try:
            # Создаем список задач для параллельной обработки монет
            tasks = [self._check_token_pump(token, threshold, tg_notify) for token, threshold in tokens.items()]
            # Запускаем все задачи параллельно, но с ограничением на 5 одновременных задач
            await asyncio.gather(*tasks)
            return False
        except Exception as ex:
            logger.error(f"Error while checking pump - {ex}")
            return False

    async def _check_token_pump(self, token: str, threshold: float, tg_notify: 'TgNotify') -> bool:
        """Проверяет "памп" для одной монеты."""
        async with self.semaphore:  # Ограничиваем количество одновременных запросов
            price_data = await self.get_price_coin(token)
            if "error" in price_data:
                logger.error(f"Error while getting price for {token}: {price_data['error']}")
                return False

            price = price_data["price"]
            prev_price, timestamp = self.price_history.get(token, (None, None))
            current_time = time.time()

            if prev_price and (current_time - timestamp) <= 15:
                percent_change = ((price - prev_price) / prev_price) * 100
                if percent_change > threshold:
                    text = f"Pump detected for {token}: price increased by {percent_change:.2f}% in {current_time - timestamp:.2f} seconds"
                    await tg_notify.tg_send_message(text)

            self.price_history[token] = (price, current_time)
            return False

class PumpObs:
    def __init__(self, price_checker: PriceChecker, tokens: dict, tg_notify):
        self.price_checker = price_checker
        self.tokens = tokens
        self.tg_notify = tg_notify

    async def start_pump(self):
        await self.price_checker.init()
        try:
            while True:
                await self.price_checker.check_pump(self.tokens, self.tg_notify)
                await asyncio.sleep(1)
        finally:
            await self.price_checker.close()


class TgNotify:
    def __init__(self, send_message: Callable[[str, int], None]):
        self.send_message = send_message
        self.thread_id: int = 242

    async def tg_send_message(self, text: str):
        await self.send_message(text, self.thread_id)


async def run_pump(send_message: Callable[[str, str], None]):
    mexc_exchange = MexcAPI()
    tg_notify = TgNotify(send_message)
    tokens = {"ONON": 7, "STONKS": 3, "CLAY": 2.50, "ALON": 4, "DHN": 3, "AKUMA": 5, "KET": 3}
    obs = PumpObs(mexc_exchange, tokens, tg_notify)
    await obs.start_pump()

# if __name__ == "__main__":
#     asyncio.run(run_pump())
# 22:49: 3,33 - 22:50: 6,48 ||
