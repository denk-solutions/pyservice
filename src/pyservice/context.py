from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar, Token
from typing import Any, ClassVar, Mapping, Self, override

from pydantic import BaseModel, ConfigDict, HttpUrl, PrivateAttr, SecretStr
from pydantic_extra_types.pendulum_dt import Duration
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContextModel(AbstractContextManager, BaseModel):
    __var__: ClassVar[ContextVar[Self]]
    """__var__ is shared across all instances of the class.
    The data backed by __var__ is only visible to the current task."""

    _token: Token[Self] | None = PrivateAttr(None)
    """_token_ records the mutation of __var__ and allows reverting to
    the previous value."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    @override
    def __enter__(self):
        if self._token is not None:
            raise RuntimeError(
                "Nesting a context model more than once is prohibited. "
                "Make sure to release the context model earlier in the call stack "
                "before entering it again."
            )
        self._token = self.__var__.set(self)
        return self

    @override
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token is None:
            raise RuntimeError("Cannot exit a context model that has not been entered.")
        self.__var__.reset(self._token)

    @classmethod
    def get(cls) -> Self | None:
        return cls.__var__.get(None)


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    "The log level @ which to log while the application is running."

    LOG_FORMAT: str = (
        "[{levelname}]|{asctime}|{name}|{filename}|{funcName}:{lineno}|{message}"
    )
    "The log format to use when logging."

    JWT_KEY: SecretStr | None = None
    "The symmetric key used to issue and verify jwt authentication tokens."

    JWT_TOKEN_ACCESS_DURATION: Duration = Duration(hours=3)
    "How long should a jwt access token be valid for."

    JWT_TOKEN_REFRESH_DURATION: Duration = Duration(days=30)
    "How long should a jwt refresh token be valid for."

    JWT_ISSUER_ID: HttpUrl | None = None
    "The issuer id encoded in jwt tokens issued by this service."

    JWT_AUDIENCE: list[str] | None = None
    "The allowed audience for jwt tokens issued by this service."

    OIDC_GOOGLE_CLIENT_ID: str | None = None
    "The client id of your service, as defined by Google."

    OIDC_APPLE_CLIENT_ID: str | None = None
    "The client id of your service, as defined by Apple."

    API_DATABASE_DRIVER: str = "postgresql+asyncpg"
    "The database dialect and DBAPI driver used to connect to the database."

    API_DATABASE_HOST: str = "localhost"
    "The host address of the database server."

    API_DATABASE_PORT: int = 5432
    "The port number of the database server."

    API_DATABASE_USER: str = "pyservice"
    "The username used to connect to the database."

    API_DATABASE_PASSWORD: SecretStr = SecretStr("pyservice")
    "The password used to connect to the database."

    API_DATABASE_NAME: str = "pyservice"
    "The name of the database to connect to."

    model_config = SettingsConfigDict(
        env_prefix="PYSERVICE_", env_file=(".env.dev", ".env")
    )


_SETTINGS_CONTEXT = None


class SettingsContext(ContextModel):
    __var__ = ContextVar("pyservice_settings")

    settings: Settings

    @override
    @classmethod
    def get(cls) -> "SettingsContext":
        assert _SETTINGS_CONTEXT is not None
        return super().get() or _SETTINGS_CONTEXT


def _create_root_settings_context():
    with SettingsContext(settings=Settings()) as ctx:
        return ctx


_SETTINGS_CONTEXT = _create_root_settings_context()


@contextmanager
def temporary_settings(updates: Mapping[str, Any]):
    ctx = SettingsContext.get()
    settings = ctx.settings.model_copy(update=updates, deep=True)
    with SettingsContext(settings=settings) as ctx:
        yield ctx
