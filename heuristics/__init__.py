from typing import Callable, Iterable

# import heuristic implementations here
from .ratio import message_to_command_ratio

# register heuristic implementations here
__all__ = ("message_to_command_ratio",)

# typing helpers
Heuristic = Callable[[Iterable[dict]], int | float]
