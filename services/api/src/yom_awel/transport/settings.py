import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
MIN_SECRET_LENGTH = 32
GEMINI_MODELS = ("gemini-2.5-flash", "gemini-2.5-flash-lite")

Mode = Literal["local", "cloud"]
FeedbackMode = Literal["auto", "fallback"]


@dataclass(frozen=True)
class Settings:
    mode: Mode = "local"
    database_path: str = ".local/learning.sqlite3"
    database_url: str = field(default="", repr=False)
    secret: str = field(default="", repr=False)
    cors_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    task_packages: Path = REPOSITORY_ROOT / "task_packages"
    gemini_api_key: str = field(default="", repr=False)
    gemini_model: str = GEMINI_MODELS[0]
    feedback_mode: FeedbackMode = "auto"
    telegram_token: str = field(default="", repr=False)
    telegram_secret: str = field(default="", repr=False)
    rate_limit: int = 120

    @property
    def uses_gemini(self) -> bool:
        return self.feedback_mode == "auto" and bool(self.gemini_api_key)

    @property
    def secure_cookies(self) -> bool:
        return self.mode == "cloud"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ
        mode = _mode(env.get("APP_ENV", "local"))
        if env.get("VERCEL") and mode == "local":
            raise ValueError("Vercel requires APP_ENV=cloud; local storage is not durable")
        feedback_mode = _feedback_mode(env.get("FEEDBACK_MODE", "") or "auto")
        secret = env.get("AUTH_SECRET", "")
        if mode == "local" and not secret:
            secret = _local_secret(Path(env.get("LOCAL_SECRET_PATH", ".local/session.key")))
        settings = cls(
            mode=mode,
            database_path=env.get("LOCAL_DATABASE_PATH", ".local/learning.sqlite3"),
            database_url=env.get("DATABASE_URL", ""),
            secret=secret,
            cors_origins=tuple(
                origin.strip()
                for origin in env.get(
                    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
                ).split(",")
                if origin.strip()
            ),
            task_packages=Path(env.get("TASK_PACKAGES_DIR", "") or cls.task_packages),
            gemini_api_key=env.get("GEMINI_API_KEY", "").strip(),
            gemini_model=env.get("GEMINI_MODEL", "") or GEMINI_MODELS[0],
            feedback_mode=feedback_mode,
            telegram_token=env.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_secret=env.get("TELEGRAM_WEBHOOK_SECRET", ""),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if len(self.secret) < MIN_SECRET_LENGTH:
            raise ValueError(f"AUTH_SECRET must have at least {MIN_SECRET_LENGTH} characters")
        if self.mode == "cloud" and not self.database_url.startswith(
            ("postgresql://", "postgres://")
        ):
            raise ValueError("APP_ENV=cloud requires a postgresql:// DATABASE_URL")
        if self.gemini_model not in GEMINI_MODELS:
            raise ValueError("GEMINI_MODEL must be gemini-2.5-flash or gemini-2.5-flash-lite")
        if not self.cors_origins:
            raise ValueError("CORS_ORIGINS must name the web app origin")
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


def _mode(value: str) -> Mode:
    if value == "local":
        return "local"
    if value == "cloud":
        return "cloud"
    raise ValueError("APP_ENV must be local or cloud")


def _feedback_mode(value: str) -> FeedbackMode:
    if value == "auto":
        return "auto"
    if value == "fallback":
        return "fallback"
    raise ValueError("FEEDBACK_MODE must be auto or fallback")


def _local_secret(path: Path) -> str:
    """A per-machine signing key for local mode, created once and never committed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(secrets.token_urlsafe(48))
        path.chmod(0o600)
    except FileExistsError:
        pass
    return path.read_text(encoding="utf-8")
