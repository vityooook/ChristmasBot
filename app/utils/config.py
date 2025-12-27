from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Bot
    bot_token: str
    bot_username: str
    
    # VPN бот (для кнопки "Подключить VPN")
    vpn_bot_username: str

    # Logging
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/christmas_bot"

    # Канал для проверки подписки (username без @)
    required_channel: str

    # ID подарка для отправки
    gift_id: str
    
    # Стоимость подарка в звёздах (для проверки баланса)
    gift_star_cost: int = 15
    
    # Минимальный баланс звёзд (предупреждение админу)
    min_star_balance: int = 100
    
    # ID админов (через запятую: "123,456,789")
    admin_ids: str = ""

    # Remnawave API (для проверки VPN)
    remnawave_api_url: str | None = None
    remnawave_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    
    def get_admin_ids(self) -> list[int]:
        """Получить список ID админов."""
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
