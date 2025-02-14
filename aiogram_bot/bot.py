from aiogram import Router, Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

# Create a router
dex_cex_spread_router = Router()

user_chat_ids = set()

@dex_cex_spread_router.message(CommandStart())
async def cmd_start(message: Message):
    chat_id = message.chat.id
    user_chat_ids.add(chat_id)

    await message.answer(
        "Hello! This is a bot to find the spread between DEX and CEX exchanges. Wait for the results...")


class TelegramBot:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.dp.include_router(dex_cex_spread_router)

    async def start(self):
        await self.dp.start_polling(self.bot)

    async def send_message(self, text: str):
        for id in user_chat_ids:
            await self.bot.send_message(chat_id=id, text=text)