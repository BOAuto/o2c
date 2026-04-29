import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    # Used for Traefik host rules in compose and to derive canonical CORS origins in prod.
    DOMAIN: str = "localhost"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        """Origins allowed for cross-origin browser calls (e.g. api.* docs, legacy SPA builds).

        Primary production path: SPA on dashboard.* uses same-origin /api (nginx -> backend),
        which does not require CORS. These entries still cover tooling, mistakes, and api.* UIs.
        """
        origins: list[str] = [
            str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS
        ]
        origins.append(self.FRONTEND_HOST.rstrip("/"))
        if self.DOMAIN:
            origins.extend(
                [
                    f"http://dashboard.{self.DOMAIN}",
                    f"https://dashboard.{self.DOMAIN}",
                    f"http://api.{self.DOMAIN}",
                    f"https://api.{self.DOMAIN}",
                ]
            )
        seen: set[str] = set()
        out: list[str] = []
        for origin in origins:
            if origin and origin not in seen:
                seen.add(origin)
                out.append(origin)
        return out

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioapp"
    MINIO_SECRET_KEY: str = "minioapp123"
    MINIO_BUCKET: str = "private-documents"
    MINIO_SECURE: bool = False
    TEMPORAL_ADDRESS: str = "temporal:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "default"
    #: Workflow cache size on the worker. Use ``0`` to disable sticky execution (no per-worker
    #: sticky task queue). That avoids Temporal server errors like "sticky worker unavailable"
    #: when the worker process restarts or is recreated (common in Docker dev). Raise in
    #: long-lived production workers if you want stickier routing and cache (e.g. ``1000``).
    TEMPORAL_WORKER_MAX_CACHED_WORKFLOWS: int = 0
    #: Connect to Temporal during API startup (Compose sets true). False avoids requiring
    #: Temporal for pytest and local runs that never touch workflow routes.
    TEMPORAL_EAGER_CONNECT: bool = False
    #: Stable workflow id for the O2C central-mail polling scheduler.
    TEMPORAL_O2C_SCHEDULER_WORKFLOW_ID: str = "o2c-ingestion-scheduler"
    #: Default poll interval when `ingestion_retrieval_period` is unset (minutes).
    O2C_DEFAULT_INGESTION_PERIOD_MINUTES: int = 5
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore
