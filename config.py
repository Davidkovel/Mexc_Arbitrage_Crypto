from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    TELEGRAM_BOT_TOKEN: str
    API_KEY: str
    API_SECRET: str
    PROXIES: List[Dict[str, str]]
    TEST_PROXIES: List[Dict[str, str]]


settings = Settings()

print("Telegram Bot Token:", settings.TELEGRAM_BOT_TOKEN)
print("API Key:", settings.API_KEY)
print("API Secret:", settings.API_SECRET)
print("Proxies:", settings.PROXIES)