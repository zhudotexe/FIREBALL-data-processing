import collections
from functools import cached_property
from typing import Callable, Hashable, Iterable, Optional

AVRAE_ID = "261302296103747584"


def is_bot_message(message):
    """Returns whether or not a message was sent by a bot."""
    return message["author_id"] == AVRAE_ID or message.get("author_bot")


def is_command_invocation(message):
    """
    Returns whether or not a message was invoking some command (based on whether it starts with a common bot prefix).
    """
    return message["content"].startswith(("!", "$", "%", "^", "&", "/", "]", "a!", "<"))


def did_turn_change(previous_state, current_state):
    """Returns whether or not the combat is on different turns in the previous and current state."""
    if previous_state is None:  # hack to prevent crashes before state init
        return False
    if previous_state["current"] is None or current_state["current"] is None:
        return previous_state["current"] != current_state["current"]
    previous_combatant_id = previous_state["combatants"][previous_state["current"]]["id"]
    current_combatant_id = current_state["combatants"][current_state["current"]]["id"]
    return previous_combatant_id != current_combatant_id


# ===== instance helpers =====
Event = dict


class MessageGroup:
    def __init__(self, message: Event):
        self.message = message
        self.events = [message]

    @classmethod
    def concat(cls, other_groups: list["MessageGroup"]):
        inst = cls(other_groups[0].message)
        inst.events = sum((g.events for g in other_groups), [])
        return inst

    # list compatibility
    def append(self, event: Event):
        self.events.append(event)

    def __iter__(self):
        yield from self.events

    def __len__(self):
        return len(self.events)

    def __getitem__(self, idx):
        return self.events[idx]

    def __hash__(self):
        return hash(self.message["message_id"])

    # helpers
    def is_only_message(self):
        """True if this message group is just a message (i.e. it did not trigger a command or anything)."""
        return len(self.events) == 1

    def has_event_of_type(self, event_type: str):
        return any(e["event_type"] == event_type for e in self.events)

    def find_event_of_type(self, event_type: str):
        return next((e for e in self.events if e["event_type"] == event_type), None)

    def find_all_of_type(self, event_type: str):
        return [e for e in self.events if e["event_type"] == event_type]


class Instance:
    """Wrapper class to help reason over entire instances. Construct with a pristine event stream."""

    def __init__(self, event_stream: Iterable[Event]):
        self.events = list(event_stream)

    @cached_property
    def message_groups(self) -> list[MessageGroup]:
        """
        Returns a list of (list of events), where every first element in the inner list is a message event
        and all other elements in the inner list are events triggered by that message event.
        """
        # we can return this since dicts are ordered
        return list(self.message_groups_by_id.values())

    @cached_property
    def message_groups_by_id(self) -> dict[str, MessageGroup]:
        """
        Returns a mapping of message IDs to events triggered by that message ID (see message_groups).
        """
        message_groups = {}
        for event in self.events:
            match event:
                case {"event_type": "message", "message_id": message_id}:
                    message_groups[message_id] = MessageGroup(event)
                case (
                    {"event_type": "command", "message_id": message_id}
                    | {"event_type": "automation_run", "interaction_id": message_id}
                    | {"event_type": "combat_state_update", "probable_interaction_id": message_id}
                    | {"event_type": "alias_resolution", "message_id": message_id}
                    | {"event_type": "snippet_resolution", "message_id": message_id}
                ) if message_id in message_groups:
                    message_groups[message_id].append(event)
        return message_groups

    def partitioned_groups(self, query: Callable[[Event], Hashable]) -> Iterable[tuple[Hashable, list[MessageGroup]]]:
        """
        Partitions message groups by some query on the message (e.g. lambda message: message["author_id"]).

        Returns an iterable of (key, MessageGroup[]) pairs.
        """
        groups = collections.defaultdict(lambda: [])
        for mgroup in self.message_groups:
            groups[query(mgroup.message)].append(mgroup)
        return groups.items()

    def filtered_groups(self, the_filter: Callable[[Event], bool]) -> Iterable[MessageGroup]:
        """Returns a list of MessageGroups such that the_filter(group.message) is True."""
        return filter(lambda mgroup: the_filter(mgroup.message), self.message_groups)

    def find(self, query: Callable[[Event], bool]) -> Optional[Event]:
        """Returns the first event such that query(event) holds, or None if no such event exists."""
        return next(filter(query, self.events), None)

    def find_all(self, query: Callable[[Event], bool]) -> Iterable[Event]:
        """Returns a list of events such that query(event) holds."""
        return filter(query, self.events)

    def find_all_of_type(self, event_type: str):
        return [e for e in self.events if e["event_type"] == event_type]

    def combat_state_at_event(self, event: Event) -> dict:
        """Returns the combat state at a current event."""
        if event not in self.events:
            raise ValueError("passed event is not in this instance")
        idx = self.events.index(event)
        for event in self.events[idx::-1]:
            if event["event_type"] == "combat_state_update":
                return event["data"]
