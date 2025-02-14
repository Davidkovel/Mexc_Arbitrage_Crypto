import asyncio
import random

async def get_price_mexc(value):
    await asyncio.sleep(random.uniform(0.5, 1.5))
    print(f'[MEXC] Price for {value}')

async def get_price_dex(value):
    await asyncio.sleep(random.uniform(0.5, 1.5))
    print(f'[DEX] Price for {value}')

async def process_prices(prices):
    for value in prices.values():
        await asyncio.gather(get_price_mexc(value), get_price_dex(value))

async def main():
    prices = {f"s{i}": i for i in range(1, 11)}
    while True:
        await process_prices(prices)
        await asyncio.sleep(random.uniform(1, 3))

if __name__ == "__main__":
    print("[INFO] Prod started")
    asyncio.run(main())
