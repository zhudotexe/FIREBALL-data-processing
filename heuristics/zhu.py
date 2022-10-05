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


def num_participants(events) -> float:
    """Returns the number of unique message authors in an event stream."""
    authors = set()
    for event in events:
        if event["event_type"] == "message":
            authors.add(event["author_id"])
    return len(authors)
