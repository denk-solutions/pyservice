import sys
from logging import Formatter, Logger, LoggerAdapter, StreamHandler, getLogger
from typing import Protocol, TextIO, cast

from pyservice.context import SettingsContext
from pyservice.version import __version__

_LOGGER: Logger | None = None


class LogMethod(Protocol):
    def __call__(self, msg: str, *args, **kwargs) -> None: ...


def __getattr__(name: str) -> LogMethod:
    """Delegate all attribute access against this module to the global _LOGGER instance."""

    def wrapper(msg: str, *args, **kwargs):
        assert _LOGGER is not None, "Logger is not initialized"
        stacklevel = 2
        if name == "exception":
            stacklevel = 3
        getattr(_LOGGER, name)(msg, *args, **kwargs, stacklevel=stacklevel)

    return wrapper


def _create_root_logger() -> Logger:
    global _LOGGER
    return _LOGGER or _create_logger("pyservice")


def _create_logger(name: str, stream: TextIO = sys.stderr) -> Logger:
    ctx = SettingsContext.get()

    lg = getLogger(name)
    lg.setLevel(ctx.settings.LOG_LEVEL)
    lg.propagate = False

    formatter = Formatter(ctx.settings.LOG_FORMAT, style="{")
    handler = StreamHandler(stream)
    handler.setFormatter(formatter)

    lg.addHandler(handler)

    lg = LoggerAdapter(lg, {"version": __version__})

    return cast(Logger, lg)


_LOGGER = _create_root_logger()
