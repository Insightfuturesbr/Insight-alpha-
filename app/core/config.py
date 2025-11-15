from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Ambiente
    ENV: str = "development"
    FLASK_ENV: str = "development"
    mongodb_uri_local: str | None = None
    mongodb_uri_atlas: str | None = None
    mongo_env: str = "local"

    # Segurança
    SECRET_KEY: str = "123"

    # Banco de dados
    DATABASE_URL: str = "sqlite:///./dev.db"

    # Diretórios (opcionais via .env)
    UPLOAD_FOLDER: str | None = None
    OUTPUTS_DIR: str | None = None
    STATIC_DIR: str | None = None
    TEMPLATES_DIR: str | None = None

    # .env (Pydantic v2)
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Helpers de caminho
    @property
    def ROOT_DIR(self) -> Path:
        # app/core/config.py → parents[2] = raiz do projeto
        return Path(__file__).resolve().parents[2]

    @property
    def WEB_DIR(self) -> Path:
        return self.ROOT_DIR / "web"

    @property
    def templates_dir(self) -> str:
        return str(Path(self.TEMPLATES_DIR) if self.TEMPLATES_DIR else (self.WEB_DIR / "templates"))

    @property
    def static_dir(self) -> str:
        return str(Path(self.STATIC_DIR) if self.STATIC_DIR else (self.WEB_DIR / "static"))

    @property
    def uploads_dir(self) -> str:
        default = self.ROOT_DIR / "uploads"
        return str(Path(self.UPLOAD_FOLDER) if self.UPLOAD_FOLDER else default)

    @property
    def outputs_dir(self) -> str:
        default = self.ROOT_DIR / "outputs"
        return str(Path(self.OUTPUTS_DIR) if self.OUTPUTS_DIR else default)


settings = Settings()
