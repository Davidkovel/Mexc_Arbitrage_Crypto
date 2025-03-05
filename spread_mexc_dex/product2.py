import asyncio
from typing import Dict, Set, Callable, Awaitable

from utils.logger import *
from spread_mexc_dex.product import DexApi, MexcAPI
from spread_mexc_dex.token_manager import TokenManager, SpreadContext


class PriceFetcher:
    def __init__(self, mexc_api: MexcAPI, dex_api: DexApi):
        self.mexc_api = mexc_api
        self.dex_api = dex_api
        # self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def fetch_prices(self, token: str, address_contract: str, chain: str) -> tuple:
        price_mexc = await self.mexc_api.get_price_coin(token)
        await asyncio.sleep(0.1)
        price_dex = await self.dex_api.get_price_coin(token, address_contract, chain)
        return token, price_mexc, price_dex


class SpreadCalculator:
    @staticmethod
    def calculate_spread(price1: float, price2: float, mexc_higher: bool = True) -> float:
        """
        Вычисляет спред с учетом направления.
        :param price1: Цена на MEXC.
        :param price2: Цена на DEX.
        :param mexc_higher: Если True, спред вычисляется только если price1 > price2.
        :return: Спред в процентах.
        """
        if price1 == 0 or price2 == 0:
            return 0.0
        if mexc_higher and price1 <= price2:  # Проверяем, что цена на MEXC выше, чем на DEX
            return 0.0
        return abs((price1 - price2) / ((price1 + price2) / 2)) * 100


class ArbitrageNotifier:
    def __init__(self, send_telegram_message: Callable[[str], Awaitable[None]]):
        self.send_telegram_message = send_telegram_message

    async def notify(self, token: str, spread: float, price_mexc: float, price_dex: float, contract_address: str,
                     chain: str):
        dex_url = f"https://dexscreener.com/{chain.lower()}/{contract_address}"
        mexc_url = f"https://futures.mexc.com/exchange?symbol={token}_USDT"

        message = (
            f"*Монета:* `{token}`\n"
            f"*Спред:* `{spread:.2f}%`\n\n"
            f"*MEXC Цена:* `{price_mexc}$`\n\n"
            f"*DEX Цена:* `{price_dex}$`\n"
            f"*Контракт:* `{contract_address}`\n"
            f"*Сеть:* `{chain}`\n\n"
            f"[🔗 Перейти на DEX]({dex_url}) | [🔗 Перейти на MEXC]({mexc_url})\n\n"
            f"🖋️ Created by [XGenius PRO]\n"
        )
        logger.info(message)
        await self.send_telegram_message(message, message_thread_id=4294967301, dex_url=dex_url, mexc_url=mexc_url)


class ArbitrageManager:
    def __init__(
            self,
            price_fetcher: PriceFetcher,
            spread_calculator: SpreadCalculator,
            arbitrage_notifier: ArbitrageNotifier,
            token_manager: TokenManager,
            mexc_exchange: MexcAPI,
            dex_exchange: DexApi
    ):
        self.price_fetcher = price_fetcher
        self.spread_calculator = spread_calculator
        self.arbitrage_notifier = arbitrage_notifier
        self.token_manager = token_manager
        self.spread_context = SpreadContext(token_manager)
        self.mexcExchange = mexc_exchange
        self.dexExchange = dex_exchange

    async def init_http_client(self):
        await self.mexcExchange.init()
        await self.dexExchange.init()

    async def process_token(self, token_info):
        try:
            token, contract_address, chain = token_info["token"], token_info["address_contract"], token_info["chain"]
            result = await self.price_fetcher.fetch_prices(token, contract_address, chain)
            token, price_mexc, price_dex = result

            # logger.info(f'CHECKING {token}, {price_mexc} - {price_dex} ')
            if "error" in price_dex or "error" in price_mexc:
                logger.error(f"[ERROR] Ошибка получения цен: {token} MEXC: {price_mexc}, DEX: {price_dex}")
                return

            spread = self.spread_calculator.calculate_spread(price_mexc["price"], price_dex["price"], mexc_higher=True)

            minimum_spread = token_info.get('minimum_spread', 6.0)
            # if spread > minimum_spread:
            #     await self.arbitrage_notifier.notify(token, spread, price_mexc["price"], price_dex["price"],
            #                                          contract_address, chain)
            #     logger.info(f"[INFO] Sleeping for 1 minute for {token} to avoid spam...")
            #     asyncio.create_task(self.token_manager.add_to_cooldown(token, 500))
            result_spread = self.spread_context.handle_spread(token, spread, minimum_spread)
            has_spread, thread_id = result_spread['Has_spread'], result_spread['thread_id']
            if has_spread:
                await self.arbitrage_notifier.notify(token, spread, price_mexc["price"], price_dex["price"],
                                                     contract_address, chain)
                logger.info(f"[INFO] Sleeping for 1 minute for {token} to avoid spam...")

                # asyncio.create_task(self.token_manager.add_to_cooldown(token, 20))
        except Exception as ex:
            logger.error(f"Failed to fetch prices for {token_info['token']}: {ex}")

    async def worker(self, queue):
        while True:
            token_info = await queue.get()  # Получаем задачу из очереди
            try:
                await self.process_token(token_info)
            finally:
                queue.task_done()  # Помечаем задачу как выполненную

    async def run_find_arbitrage(self):
        await self.init_http_client()
        queue = asyncio.Queue()  # Создаем очередь задач

        # Создаем и запускаем воркеры
        workers = [asyncio.create_task(self.worker(queue)) for _ in range(10)]  # 10 воркеров

        while True:
            tokens = self.token_manager.get_tokens()

            # Добавляем задачи в очередь
            for token, details in tokens.items():
                token_info = {
                    "token": token,
                    "address_contract": details['contract_address'],
                    "chain": details['chain'],
                    "minimum_spread": details.get('minimum_spread', 6.0)
                }
                await queue.put(token_info)  # Добавляем токен в очередь

            # Ждем, пока все задачи в очереди будут выполнены
            await queue.join()

            logger.info('Sleeping for 30 seconds before the next iteration...')
            await asyncio.sleep(30)

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
