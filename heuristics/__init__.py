from typing import Callable, Iterable

# import heuristic implementations here
from .count import event_count, message_count
from .ratio import message_to_command_ratio, average_message_length

# register heuristic implementations here
__all__ = (
    "event_count",
    "message_count",
    "message_to_command_ratio",
    "average_message_length",
)

# typing helpers
Heuristic = Callable[[Iterable[dict]], int | float]
