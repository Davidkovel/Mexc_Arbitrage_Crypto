import asyncio

from aiogram_bot.bot import TelegramBot
from kafka.consumer import ArbitrageConsumer

from pump_mexc.main_pump_mexc import run_pump
from utils.logger import *
from config import settings

TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN


async def run_bot(telegram_bot: TelegramBot):
    """
    Start the Telegram bot.
    """
    await telegram_bot.start()


async def main():
    telegram_bot = TelegramBot(token=TELEGRAM_BOT_TOKEN)

    arbitrage_kafka_consumer = ArbitrageConsumer(
        bootstrap_servers=settings.KAFKA_SERVER_HOST,
        topic="arbitrage_dex_cex-notifications",
        group_id="arbitrage_dex_cex-notifications",
        telegram_bot=telegram_bot
    )

    try:
        # await telegram_bot.send_message('fdsfdsfds', 4294967301)
        await asyncio.gather(
            run_bot(telegram_bot),  # Запуск бота
            arbitrage_kafka_consumer.start()
        )
    finally:
        await arbitrage_kafka_consumer.stop()
        # await arbitrage_manager.deconstruct_http_client()
        # await telegram_bot.close()


def turn_off_debug():
    logger.remove()


if __name__ == "__main__":
    print("[INFO] Prod started")

    if not hasattr(settings, 'KAFKA_BOOTSTRAP_SERVERS'):
        settings.KAFKA_SERVER_HOST = 'localhost:9092'

    asyncio.run(main())

# ПЛАНИ:
# 1. env файл сделать
# 2. Сделать конфиг файл
# 3. Сделать докер файл
# 4. Закинуть на сервер мб CI/CD
