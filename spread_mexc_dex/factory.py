from abc import ABC, abstractmethod
from typing import Callable, Awaitable

from spread_mexc_dex.parse_json import JsonParse
from spread_mexc_dex.product import MexcAPI, DexApi
from spread_mexc_dex.product2 import ArbitrageManager, PriceFetcher, SpreadCalculator, TokenManager, ArbitrageNotifier


class AbstractFactory(ABC):
    @abstractmethod
    def create_arbitrage_manager(self) -> ArbitrageManager:
        pass


class ArbitrageFactory(AbstractFactory):
    def __init__(self, send_telegram_message: Callable[[str], Awaitable[None]]):
        self.send_telegram_message = send_telegram_message

    def create_arbitrage_manager(self) -> ArbitrageManager:
        parser = JsonParse()
        list_tokens = parser.parse()

        # Создаем API для бирж
        mexc_api = MexcAPI()
        dex_api = DexApi()

        # Ззависимости для ArbitrageManager
        price_fetcher = PriceFetcher(mexc_api, dex_api)
        spread_calculator = SpreadCalculator()
        arbitrage_notifier = ArbitrageNotifier(self.send_telegram_message)
        token_manager = TokenManager(list_tokens)

        return ArbitrageManager(
            price_fetcher=price_fetcher,
            spread_calculator=spread_calculator,
            arbitrage_notifier=arbitrage_notifier,
            token_manager=token_manager,
            mexcExchange=mexc_api,
            dexExchange=dex_api,
        )