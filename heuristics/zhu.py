import itertools

from .utils import is_bot_message, is_command_invocation


def avg_num_words_between_commands(events) -> float:
    """
    Returns the average number of words (in messages not sent by a bot and not starting with punctuation) between Avrae
    commands.
    """
    count = 0
    counts = []
    for event in events:
        if event["event_type"] == "command":
            counts.append(count)
            count = 0
        elif event["event_type"] == "message" and not is_bot_message(event) and not is_command_invocation(event):
            count += len(event["content"].split(" "))

    counts.append(count)
    return (sum(counts) / len(counts)) if counts else 0


def words_between_commands_excl_last(events) -> float:
    """
    Same as avg_num_words_between_commands, but excluding the last buffer.
    """
    count = 0
    counts = []
    for event in events:
        if event["event_type"] == "command":
            counts.append(count)
            count = 0
        elif event["event_type"] == "message" and not is_bot_message(event) and not is_command_invocation(event):
            count += len(event["content"].split(" "))

    return (sum(counts) / len(counts)) if counts else 0


def num_participants(events) -> float:
    """Returns the number of unique message authors in an event stream."""
    authors = set()
    for event in events:
        if event["event_type"] == "message":
            authors.add(event["author_id"])
    return len(authors)


def num_actors(events) -> float:
    """Returns the number of initiative actors in an event stream."""
    actor_ids = set()
    for event in events:
        if event["event_type"] == "combat_state_update":
            combat = event["data"]
            for actor in combat["combatants"]:
                if actor["type"] == "group":
                    actor_ids.update({group_actor["id"] for group_actor in actor["combatants"]})
                else:
                    actor_ids.add(actor["id"])

    return len(actor_ids)


def num_player_actors(events) -> float:
    """Returns the number of player actors in an event stream."""
    return sum(1 for event in events if event["event_type"] == "command" and event["command_name"] == "init join")


def num_monster_actors(events) -> float:
    """Returns the number of monster actors in an event stream."""
    actor_ids = set()
    for event in events:
        if event["event_type"] == "combat_state_update":
            combat = event["data"]
            for actor in combat["combatants"]:
                if actor["type"] == "group":
                    actor_ids.update(
                        {group_actor["id"] for group_actor in actor["combatants"] if group_actor["type"] == "monster"}
                    )
                elif actor["type"] == "monster":
                    actor_ids.add(actor["id"])

    return len(actor_ids)


def player_to_monster_ratio(events) -> float:
    """
    Returns the ratio of players to monsters in an event stream.
    Returns 255 as a sentinel value if there are no monsters.
    WARNING: eats a lot of memory due to consuming the iterator twice.
    """
    e1, e2 = itertools.tee(events)
    num_player = num_player_actors(e1)
    num_monster = num_monster_actors(e2)
    return 255 if not num_monster else (num_player / num_monster)


def num_turns(events) -> float:
    """Returns the number of combat turns in an event stream."""
    return sum(1 for event in events if event["event_type"] == "command" and event["command_name"] == "init next")


def num_words_per_turn(events) -> float:
    """
    Returns the average number of words per combat turn, excluding the last turn (to avoid "forgetting to end"
    outliers).
    """
    count = 0
    counts = []
    for event in events:
        if event["event_type"] == "command" and event["command_name"] == "init next":
            counts.append(count)
            count = 0
        elif event["event_type"] == "message" and not is_bot_message(event) and not is_command_invocation(event):
            count += len(event["content"].split(" "))

    return (sum(counts) / len(counts)) if counts else 0
