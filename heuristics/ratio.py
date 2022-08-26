def message_to_command_ratio(events) -> float:
    """Returns the proportion of messages that were valid command invocations."""
    message_count = 0
    command_count = 0
    for event in events:
        match event["event_type"]:
            case "message":
                message_count += 1
            case "command":
                command_count += 1

    return command_count / message_count


def average_message_length(events) -> float:
    """Returns the average length of non-bot messages."""
    lens = []
    for event in events:
        if (
            event["event_type"] == "message"
            and event["author_id"] != "261302296103747584"  # not a bot message
            and not event["content"].startswith("!")  # and not a bot command invocation
        ):
            lens.append(len(event["content"].split(" ")))
    return (sum(lens) / len(lens)) if lens else 0
