from .connection import get_session
from .model import Script, Step
from .player import play

__all__ = ["get_session", "Script", "Step", "play", "Recorder"]


def __getattr__(name):
    if name == "Recorder":
        from .recorder import Recorder

        return Recorder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
