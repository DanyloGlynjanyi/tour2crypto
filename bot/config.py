import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str = (os.getenv("BOT_TOKEN") or "").strip()
    DB_PATH: str = os.getenv("DB_PATH", str(PROJECT_ROOT / "data" / "t2c.sqlite3"))
    PUBLIC_REDIRECT_BASE: str = os.getenv("PUBLIC_REDIRECT_BASE", "http://127.0.0.1:8000/r")
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "TOUR2CRYPTO")
    ADMIN_IDS: tuple[str, ...] = tuple(x.strip() for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip())

settings = Settings()
if not settings.BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is empty in .env")
