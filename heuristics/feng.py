from .utils import is_bot_message, is_command_invocation

def avg_time_between_message_and_command(events) -> float:
    """Returns the average number of events between each command call and the last non-command message from its author"""
    dists = []
    last_noncommand = {}
    for event in events:
        if (
            event["event_type"] == "message"
            and not is_bot_message(event)
            and not is_command_invocation(event)
        ):
            last_noncommand[event["author_id"]] = event["timestamp"] # record the timestamp of the last message for each author
        elif event["event_type"] == "command" and not is_bot_message(event):
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
            and not is_bot_message(event)
            and not is_command_invocation(event)
        ):
            messaged[event["author_id"]] = True # record the timestamp of the last message for each author
        elif event["event_type"] == "command" and not is_bot_message(event):
            commands += 1
            if not messaged.get(event["author_id"],0):
                messageless_commands += 1
    
    if commands > 0: return messageless_commands/commands
    return 0

