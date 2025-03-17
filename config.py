import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="./.env")

    TELEGRAM_BOT_TOKEN: str
    KAFKA_SERVER_HOST: str


settings = Settings()
# print("Telegram Bot Token:", settings.TELEGRAM_BOT_TOKEN)
# print("API Key:", settings.API_KEY)
# print("API Secret:", settings.API_SECRET)
# print("Proxies:", settings.PROXIES)
