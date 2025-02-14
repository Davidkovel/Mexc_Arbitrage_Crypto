import asyncio

from spread_mexc_dex.factory import AbstractFactory, ArbitrageFactory
from aiogram_bot.bot import TelegramBot

TELEGRAM_BOT_TOKEN = "7830389967:AAFQBi_XlJo69NcbjSUXRgMsn77hhw_33MA"


async def run_bot(telegram_bot: TelegramBot):
    """
    Start the Telegram bot.
    """
    await telegram_bot.start()


async def run_arbitrage(factory: AbstractFactory):
    """
    Run the arbitrage manager.
    """
    product = factory.create_arbitrage_manager()
    await product.run_find_arbitrage()


async def main():
    """
    Run both the bot and the arbitrage manager concurrently.
    """
    telegram_bot = TelegramBot(token=TELEGRAM_BOT_TOKEN)

    factory = ArbitrageFactory(telegram_bot.send_message)

    try:
        await asyncio.gather(
            run_bot(telegram_bot),  # Запуск бота
            run_arbitrage(factory)  # Запуск менеджера арбитража
        )
    finally:
        pass
        # await arbitrage_manager.deconstruct_http_client()
        # await telegram_bot.close()

if __name__ == "__main__":
    print("[INFO] Prod started")
    asyncio.run(main())

    # SWFTC