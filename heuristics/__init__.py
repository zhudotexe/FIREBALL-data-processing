from typing import Callable, Iterable

# import heuristic implementations here
from .count import event_count, message_count
from .feng import avg_time_between_message_and_command, ratio_of_commands_without_message
from .ratio import average_message_length, message_to_command_ratio
from .zhu import (
    avg_num_words_between_commands,
    num_actors,
    num_monster_actors,
    num_participants,
    num_player_actors,
    num_turns,
    num_words_per_turn,
    player_to_monster_ratio,
    words_between_commands_excl_last,
)

# register heuristic implementations here
__all__ = (
    # simple
    "event_count",
    "message_count",
    "message_to_command_ratio",
    "average_message_length",
    # zhu
    "avg_num_words_between_commands",
    "num_participants",
    "num_turns",
    "num_words_per_turn",
    "num_actors",
    "num_player_actors",
    "num_monster_actors",
    "player_to_monster_ratio",
    "words_between_commands_excl_last",
    # feng
    "avg_time_between_message_and_command",
    "ratio_of_commands_without_message",
)

# typing helpers
Heuristic = Callable[[Iterable[dict]], int | float]
