from dataclasses import dataclass

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import expression
from sqlalchemy.types import DateTime, String, Text, TypeDecorator

from pyservice.auth.context import HashContext


class utcnow(expression.FunctionElement):
    type = DateTime()
    inherit_cache = True


@compiles(utcnow, "postgresql")
def pg_utcnow(element, compiler, **kw):
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


@dataclass
class UserIdentity:
    provider: str
    id: str

    def __str__(self):
        return f"{self.provider}:{self.id}"

    @classmethod
    def from_string(cls, value: str):
        provider, id = value.split(":", 1)
        return cls(provider, id)


class UserIdentityType(TypeDecorator):
    impl = String(255)

    def process_bind_param(self, value, dialect):
        return self._convert(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        assert isinstance(value, str)
        return UserIdentity.from_string(value)

    def _convert(self, value):
        if isinstance(value, UserIdentity):
            return f"{value.provider}:{value.id}"
        if isinstance(value, str):
            return value
        if value is not None:
            raise TypeError(f"Cannot convert {type(value)} to UserIdentity")
        return value


class PasswordHashType(TypeDecorator):
    impl = Text

    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        if not isinstance(value, (str, bytes)):
            raise TypeError(f"Cannot convert {type(value)} to PasswordHash")

        ctx = HashContext.get()
        return ctx.crypt.hash(value)

    def process_result_value(self, value, dialect):
        return value
