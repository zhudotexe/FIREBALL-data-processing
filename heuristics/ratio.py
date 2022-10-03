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

def average_time_between_message_and_command(events) -> float:
    """Returns the average number of events between each command call and the last non-command message from its author"""
    dists = []
    last_noncommand = {}
    for event in events:
        if (
            event["event_type"] == "message"
            and event["author_id"] != "261302296103747584"  # not a bot message
            and not event["content"].startswith("!")  # and not a bot command invocation
        ):
            last_noncommand[event["author_id"]] = event["timestamp"] # record the timestamp of the last message for each author
        elif event["event_type"] == "command" and event["author_id"] != "261302296103747584":
            if event["author_id"] in last_noncommand.keys():
                dists.append(event["timestamp"]-last_noncommand[event["author_id"]])
    return (sum(dists) / len(dists)) if dists else 0

def ratio_of_commands_without_message(events) -> float:
    """Return the number """
    commands, messageless_commands = 0,0
    messaged = {}
    for event in events:
        if (
            event["event_type"] == "message"
            and event["author_id"] != "261302296103747584"  # not a bot message
            and not event["content"].startswith("!")  # and not a bot command invocation
        ):
            messaged[event["author_id"]] = True # record the timestamp of the last message for each author
        elif event["event_type"] == "command"and event["author_id"] != "261302296103747584":
            commands += 1
            if not messaged.get(event["author_id"],0):
                messageless_commands += 1
    
    if commands > 0: return messageless_commands/commands
    return 0

