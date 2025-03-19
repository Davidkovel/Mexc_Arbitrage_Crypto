from fastapi import FastAPI, Depends
from pydantic import BaseModel
import uvicorn
from aiogram_bot.bot import TelegramBot

app = FastAPI()


class Notification(BaseModel):
    formatted_message: str
    thread_id: int
    dex_url: str
    mexc_url: str


class ArbitrageConsumerRestApi:
    def __init__(self, telegram: TelegramBot):
        self.telegram_bot = telegram

    async def send_notification(self, notification: Notification):
        """
        Отправка уведомления в Telegram.
        """
        await self.telegram_bot.send_message(
            text=notification.formatted_message,
            message_thread_id=notification.thread_id,
            dex_url=notification.dex_url,
            mexc_url=notification.mexc_url
        )


# Эндпоинт для создания уведомления
@app.post("/notifications/")
async def create_notification(
        notification: Notification,
        consumer: ArbitrageConsumerRestApi = Depends(lambda: app.state.consumer)
):
    """
    Эндпоинт для создания уведомления (аналог Kafka Producer).
    """
    await consumer.send_notification(notification)
    return {"message": "Notification received", "data": notification}


async def web_app_start(telegram_bot: TelegramBot):
    """
    Запуск FastAPI приложения.
    """
    # Создаем экземпляр ArbitrageConsumerRestApi и сохраняем его в состоянии приложения
    app.state.consumer = ArbitrageConsumerRestApi(telegram_bot)

    # Запуск сервера
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()
