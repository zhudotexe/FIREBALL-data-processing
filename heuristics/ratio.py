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
