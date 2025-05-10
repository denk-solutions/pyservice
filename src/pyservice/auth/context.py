from contextvars import ContextVar
from typing import override

from passlib.context import CryptContext

from pyservice.context import ContextModel

_HASH_CONTEXT = None


class HashContext(ContextModel):
    __var__ = ContextVar("pyservice_hash")

    crypt: CryptContext

    @override
    @classmethod
    def get(cls) -> "HashContext":
        assert _HASH_CONTEXT is not None
        return super().get() or _HASH_CONTEXT


def _create_hash_context():
    with HashContext(crypt=CryptContext(schemes=["sha256_crypt"])) as ctx:
        return ctx


_HASH_CONTEXT = _create_hash_context()
