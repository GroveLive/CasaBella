# config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_NAME: str
    DATABASE_URL: str = ""

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    APP_PORT: int = 8001

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def constructed_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+psycopg2://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

settings = Settings()

class Config:
    SQLALCHEMY_DATABASE_URI = settings.constructed_database_url
    SECRET_KEY = settings.SECRET_KEY
    # Agrega más configuraciones si las necesitas, por ejemplo:
    # WTF_CSRF_ENABLED = True
