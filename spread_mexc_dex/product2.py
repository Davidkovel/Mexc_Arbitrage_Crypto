import asyncio
from typing import Dict, Set, Callable, Awaitable
from spread_mexc_dex.product import DexApi, MexcAPI


class PriceFetcher:
    def __init__(self, mexc_api: MexcAPI, dex_api: DexApi, max_concurrent_requests: int = 10):
        self.mexc_api = mexc_api
        self.dex_api = dex_api
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    # async def fetch_prices(self, token: str, address_contract: str, chain: str) -> tuple:
    #     price_mexc = await self.mexc_api.get_price_coin(token)
    #     price_dex = await self.dex_api.get_price_coin(token, address_contract, chain)
    #     return token, price_mexc, price_dex

    async def fetch_prices(self, token: str, address_contract: str, chain: str) -> tuple:
        async with self.semaphore:  # Ограничиваем количество одновременных запросов
            # Запрашиваем цену с MEXC
            price_mexc = await self.mexc_api.get_price_coin(token)
            # Ждем 0.1 секунды перед запросом к DEX
            await asyncio.sleep(0.1)
            # Запрашиваем цену с DEX
            price_dex = await self.dex_api.get_price_coin(token, address_contract, chain)
            return token, price_mexc, price_dex


class SpreadCalculator:
    @staticmethod
    def calculate_spread(price1: float, price2: float) -> float:
        if price1 == 0 or price2 == 0:
            return 0.0
        return abs((price1 - price2) / ((price1 + price2) / 2)) * 100


class ArbitrageNotifier:
    def __init__(self, send_telegram_message: Callable[[str], Awaitable[None]]):
        self.send_telegram_message = send_telegram_message

    async def notify(self, token: str, spread: float, price_mexc: float, price_dex: float):
        message = (
            f"[INFO] Arbitrage found for {token}: Spread = {spread:.2f}%\n"
            f"📈 Mexc Price: {price_mexc}\n"
            f"📉 Dex Price: {price_dex}"
        )
        print(message)
        await self.send_telegram_message(message)


class TokenManager:
    def __init__(self, list_tokens: Dict[str, dict]):
        self.list_tokens = list_tokens
        self.cooldown_tokens: Set[str] = set()

    def get_tokens(self) -> Dict[str, dict]:
        return {k: v for k, v in self.list_tokens.items() if k not in self.cooldown_tokens}

    async def add_to_cooldown(self, token: str, cooldown_time: int):
        self.cooldown_tokens.add(token)
        await asyncio.sleep(cooldown_time)
        self.cooldown_tokens.remove(token)
        print(f"[INFO] {token} is back in rotation")


class ArbitrageManager:
    def __init__(
        self,
        price_fetcher: PriceFetcher,
        spread_calculator: SpreadCalculator,
        arbitrage_notifier: ArbitrageNotifier,
        token_manager: TokenManager,
        mexcExchange: MexcAPI,
        dexExchange: DexApi
    ):
        self.price_fetcher = price_fetcher
        self.spread_calculator = spread_calculator
        self.arbitrage_notifier = arbitrage_notifier
        self.token_manager = token_manager
        self.mexcExchange = mexcExchange
        self.dexExchange = dexExchange

    async def init_http_client(self):
        await self.mexcExchange.init()
        await self.dexExchange.init()

    async def run_find_arbitrage(self):
        await self.init_http_client()
        while True:
            tasks = []
            tokens = self.token_manager.get_tokens()

            for token, details in tokens.items():
                token_info = {
                    "token": token,
                    "address_contract": details['contract_address'],
                    "chain": details['chain']
                }


                try:
                    # Запрашиваем цены для текущего токена
                    result = await self.price_fetcher.fetch_prices(**token_info)
                    token, price_mexc, price_dex = result

                    if "error" in price_dex or "error" in price_mexc:
                        print(f"[ERROR] Ошибка получения цен: {token} MEXC: {price_mexc}, DEX: {price_dex}")
                        continue

                    # Вычисляем спред
                    spread = self.spread_calculator.calculate_spread(price_mexc["price"], price_dex["price"])

                    # Если спред больше 7%, уведомляем
                    if spread > 7:
                        await self.arbitrage_notifier.notify(token, spread, price_mexc["price"], price_dex["price"])
                        print(f"[INFO] Sleeping for 1 minute for {token} to avoid spam...")
                        asyncio.create_task(self.token_manager.add_to_cooldown(token, 120))

                except Exception as ex:
                    print(f"[ERROR] Failed to fetch prices for {token}: {ex}")

            # Пауза между итерациями
            print('Sleeping for 10 seconds before the next iteration...')
            await asyncio.sleep(100)

            #     tasks.append(self.price_fetcher.fetch_prices(**token_info))
            #     await asyncio.sleep(0.05)
            #
            # # results = await asyncio.gather(*tasks, return_exceptions=True)
            # for task in asyncio.as_completed(tasks):
            #     try:
            #         result = await task
            #         token, price_mexc, price_dex = result
            #         if isinstance(result, Exception):
            #             print(f"[ERROR] Failed to fetch prices: {result}")
            #             continue
            #
            #         if "error" in price_dex or "error" in price_mexc:
            #             print(f"[ERROR] Ошибка получения цен: {token} MEXC: {price_mexc}, DEX: {price_dex}")
            #             continue
            #
            #         spread = self.spread_calculator.calculate_spread(price_mexc["price"], price_dex["price"])
            #
            #         if spread > 7:
            #             await self.arbitrage_notifier.notify(token, spread, price_mexc["price"], price_dex["price"])
            #             print(f"[INFO] Sleeping for 1 minute for {token} to avoid spam...")
            #             asyncio.create_task(self.token_manager.add_to_cooldown(token, 120))
            #     except Exception as ex:
            #         print(f"[ERROR] Failed to fetch prices: {ex}")
            #
            # print('sleeping')
            # await asyncio.sleep(10)




#
#
# class ArbitrageManager:
#     def __init__(self):
#         parser = JsonParse()
#         self.mexcExchange = MexcAPI()
#         self.dexExchange = DexApi()
#         self.list_tokens: dict = parser.parse()
#         self.cooldown_tokens = set()
#
#     async def init_http_client(self):
#         await self.mexcExchange.init()
#         await self.dexExchange.init()
#
#     async def fetch_prices(self, **kwargs):
#         token = kwargs["token"]
#         address_contract = kwargs["address_contract"]
#         chain = kwargs["chain"]
#
#         price_mexc = await self.mexcExchange.get_price_coin(token)
#         price_dex = await self.dexExchange.get_price_coin(token, address_contract, chain)
#         return token, price_mexc, price_dex
#
#     @staticmethod
#     def calculate_spread(price1: float, price2: float) -> float:
#         """
#         Рассчитывает спред между двумя ценами в процентах.
#         """
#         # print(f"Price1: {price1}, Price2: {price2}")
#         if price1 == 0 or price2 == 0:
#             return 0.0
#         return abs((price1 - price2) / ((price1 + price2) / 2)) * 100
#
#     async def run_find_arbitrage(self, send_telegram_message):
#         await self.init_http_client()
#
#         while True:
#             tasks = []  # List of tasks for asyncio
#
#             for token, details in self.list_tokens.items():
#                 if token in self.cooldown_tokens:
#                     continue
#
#                 token_info = {
#                     "token": token,
#                     "address_contract": details['contract_address'],
#                     "chain": details['chain']
#                 }
#                 tasks.append(self.fetch_prices(**token_info))
#
#             # Запускаем все задачи параллельно
#             results = await asyncio.gather(*tasks, return_exceptions=True)
#
#             for result in results:
#                 if isinstance(result, Exception):
#                     print(f"[ERROR] Failed to fetch prices: {result}")
#                     continue
#
#                 token, price_mexc, price_dex = result
#
#                 if "error" in price_dex or "error" in price_mexc:
#                     print(f"[ERROR] Ошибка получения цен: MEXC: {price_mexc}, DEX: {price_dex}")
#                     return
#
#                 spread = self.calculate_spread(price_mexc["price"], price_dex["price"])
#
#                 if spread > 7:
#                     message = (
#                         f"[INFO] Arbitrage found for {token}: Spread = {spread:.2f}%\n"
#                         f"📈 Mexc Price: {price_mexc['price']}\n"
#                         f"📉 Dex Price: {price_dex['price']}"
#                     )
#                     await send_telegram_message(message)
#
#                     print(f"[INFO] Sleeping for 1 minute for {token} to avoid spam...")
#
#                     self.cooldown_tokens.add(token)
#                     asyncio.create_task(self.remove_from_cooldown(token))
#
#                 #     print(f"[INFO] Arbitrage found for {token}: Spread = {spread:.2f}%")
#                 #     print(f"  Mexc Price: {price_mexc['price']}, Dex Price: {price_dex['price']}")
#                 # else:
#                 #     print(f"[INFO] No arbitrage for {token}: Spread = {spread:.2f}%")
#             # print('---')
#             await asyncio.sleep(12)
#             # await self.deconstruct_http_client()
#
#     async def remove_from_cooldown(self, token):
#         await asyncio.sleep(140)  # Ждем минуту
#         self.cooldown_tokens.remove(token)  # Убираем токен из списка тайм-аута
#         print(f"[INFO] {token} is back in rotation")
#
#     async def deconstruct_http_client(self):
#         await self.mexcExchange.close()
#         await self.dexExchange.close()
