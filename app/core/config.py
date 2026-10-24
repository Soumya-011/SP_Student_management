from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    PROJECT_NAME: str = "Coaching Center Management System"

    # ── Superuser / Migrator credentials (used only by migration.py) ──────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # ── Migrator role credentials (migration.py connects as this to CREATE tables)
    MIGRATOR_DB_USER: Optional[str] = None
    MIGRATOR_DB_PASSWORD: Optional[str] = None

    # ── App role credentials (FastAPI connects as this at runtime — DML only) ──
    APP_DB_USER: Optional[str] = None
    APP_DB_PASSWORD: Optional[str] = None

    # Optional full URL override (useful for cloud deployment)
    DATABASE_URL: Optional[str] = None

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    @property
    def sqlalchemy_database_url(self) -> URL | str:
        """
        Constructs the runtime PostgreSQL connection URL.
        Uses APP_DB_USER / APP_DB_PASSWORD (least-privilege app role) when set;
        falls back to DB_USER / DB_PASSWORD if the app role is not yet configured.
        Special characters in passwords are safely escaped by URL.create().
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        user = self.APP_DB_USER or self.DB_USER
        password = self.APP_DB_PASSWORD or self.DB_PASSWORD
        return URL.create(
            drivername="postgresql+psycopg2",
            username=user,
            password=password,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    @property
    def superuser_database_url(self) -> URL | str:
        """
        Constructs a connection URL using the superuser credentials (DB_USER/DB_PASSWORD).
        Used exclusively by migration.py to create roles and grant privileges.
        """
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    @property
    def migrator_database_url(self) -> URL | str:
        """
        Constructs a connection URL for the migrator role (coaching_migrator).
        Used exclusively by migration.py to run Base.metadata.create_all().
        """
        user = self.MIGRATOR_DB_USER or self.DB_USER
        password = self.MIGRATOR_DB_PASSWORD or self.DB_PASSWORD
        return URL.create(
            drivername="postgresql+psycopg2",
            username=user,
            password=password,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
