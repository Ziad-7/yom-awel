import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    mode: str = "local"
    database_path: str = ".local/learning.sqlite3"
    secret: str = ""
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    supabase_url: str = ""
    telegram_token: str = ""
    telegram_secret: str = ""
    cloud_factory: str = ""
    rate_limit: int = 120

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("APP_ENV", "local")
        if os.getenv("VERCEL") and mode == "local":
            raise ValueError("Vercel requires cloud composition; local storage is not durable")
        secret = os.getenv("LOCAL_AUTH_SECRET", "")
        if mode == "local" and not secret:
            import secrets

            path = Path(os.getenv("LOCAL_SECRET_PATH", ".local/session.key"))
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with path.open("x", encoding="utf-8") as stream:
                    stream.write(secrets.token_urlsafe(48))
            except FileExistsError:
                pass
            secret = path.read_text(encoding="utf-8")
        settings = cls(
            mode=mode,
            secret=secret,
            database_path=os.getenv("LOCAL_DATABASE_PATH", ".local/learning.sqlite3"),
            cors_origins=tuple(
                x.strip()
                for x in os.getenv(
                    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
                ).split(",")
                if x.strip()
            ),
            supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
            cloud_factory=os.getenv("CLOUD_SERVICES_FACTORY", ""),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.mode not in ("local", "cloud"):
            raise ValueError("APP_ENV must be local or cloud")
        if self.mode == "local" and len(self.secret) < 32:
            raise ValueError("LOCAL_AUTH_SECRET must have at least 32 characters")
        if self.mode == "cloud" and not self.supabase_url.startswith("https://"):
            raise ValueError("Cloud requires an HTTPS Supabase URL")
        for origin in self.cors_origins:
            parsed = urlparse(origin)
            if (
                parsed.scheme not in ("http", "https")
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in origin
            ):
                raise ValueError("CORS requires exact origins")
            if self.mode == "cloud" and parsed.scheme != "https":
                raise ValueError("Cloud origins must use HTTPS")
