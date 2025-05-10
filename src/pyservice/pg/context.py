from contextvars import ContextVar
from typing import override

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from pyservice.context import ContextModel, SettingsContext

_DATABASE_CONTEXT = None


class DatabaseContext(ContextModel):
    __var__ = ContextVar("pyservice_database")

    engine: AsyncEngine
    "engine is the connection pool used for database operations."

    @override
    @classmethod
    def get(cls) -> "DatabaseContext":
        assert _DATABASE_CONTEXT is not None
        return super().get() or _DATABASE_CONTEXT

    def session(self) -> AsyncSession:
        return AsyncSession(self.engine, expire_on_commit=False, autobegin=False)


def get_database_url():
    ctx = SettingsContext.get()

    driver = ctx.settings.API_DATABASE_DRIVER
    user = ctx.settings.API_DATABASE_USER
    password = ctx.settings.API_DATABASE_PASSWORD.get_secret_value()
    host = ctx.settings.API_DATABASE_HOST
    port = ctx.settings.API_DATABASE_PORT
    name = ctx.settings.API_DATABASE_NAME

    return f"{driver}://{user}:{password}@{host}:{port}/{name}"


def _create_root_database_context() -> DatabaseContext:
    database_url = get_database_url()
    engine = create_async_engine(database_url)
    with DatabaseContext(engine=engine) as ctx:
        return ctx


_DATABASE_CONTEXT = _create_root_database_context()
