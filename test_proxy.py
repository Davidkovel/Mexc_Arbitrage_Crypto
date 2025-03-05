import aiohttp
import asyncio
from aiohttp import BasicAuth
import random

from config import settings

proxies = settings.TEST_PROXY


class TestProxy:
    def __init__(self):
        self.session = None
        self.proxy_index = 0  # Индекс текущего прокси

    async def init(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def check_proxy(self):
        count = 0
        while True:
            proxy_info = proxies[self.proxy_index]
            proxy_url = proxy_info["url"]
            proxy_auth = BasicAuth(proxy_info["login"], proxy_info["password"])

            print(f"Используем прокси: {proxy_url}")

            try:
                async with self.session.get(
                    "https://api.dexscreener.com/token-pairs/v1/Ethereum/0xa02C49Da76A085e4E1EE60A6b920dDbC8db599F4",
                    proxy=proxy_url,
                    proxy_auth=proxy_auth,
                ) as response:
                    if response.status == 429:
                        print(f"Лимит запросов (429). Меняем прокси...")
                        self.proxy_index = (self.proxy_index + 1) % len(proxies)  # Переход к следующему прокси
                        delay = 2 + random.uniform(0, 2)  # Ждем 2-4 секунды
                        print(f"Ждем {delay:.2f} сек перед повторной попыткой...")
                        await asyncio.sleep(delay)
                        continue

                    print(f"Статус ответа: {response.status}")
                    if count % 5 == 0:
                        self.proxy_index = (self.proxy_index + 1) % len(proxies)  # Меняем прокси
                        await asyncio.sleep(7)  # Ждем перед новой попыткой
                    if response.status == 200:
                        count += 1


            except Exception as e:
                print(f"Ошибка при запросе: {e}")
                self.proxy_index = (self.proxy_index + 1) % len(proxies)  # Меняем прокси
                await asyncio.sleep(2)  # Ждем перед новой попыткой

        print("Не удалось получить данные после всех попыток.")


async def main():
    test_proxy = TestProxy()
    await test_proxy.init()
    await test_proxy.check_proxy()
    await test_proxy.close()


if __name__ == "__main__":
    asyncio.run(main())
