from aiogram import Router, Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

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

    async def send_message(self, text: str, message_thread_id: int, dex_url: str, mexc_url: str):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 DEX", url=dex_url), InlineKeyboardButton(text="🔗 Mexc", url=mexc_url)],
        ])

        await self.bot.send_message(chat_id=-1002356096487, text=text, message_thread_id=message_thread_id,
                                    reply_markup=keyboard, parse_mode="Markdown")
