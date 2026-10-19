from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    PROJECT_NAME: str = "Coaching Center Management System"

    # Individual Database Variables
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # Optional full URL override (useful for cloud deployment later)
    DATABASE_URL: Optional[str] = None

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    @property
    def sqlalchemy_database_url(self) -> URL | str:
        """
        Safely constructs the PostgreSQL connection URL, automatically
        escaping special characters (@, :, /) in DB_PASSWORD.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()