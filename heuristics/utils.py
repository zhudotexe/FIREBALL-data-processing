AVRAE_ID = "261302296103747584"


def is_bot_message(message):
    """Returns whether or not a message was sent by a bot."""
    return message["author_id"] == AVRAE_ID or message.get("author_bot")


def is_command_invocation(message):
    """
    Returns whether or not a message was invoking some command (based on whether it starts with a common bot prefix).
    """
    return message["content"].startswith(("!", "$", "%", "^", "&", "/", "]", "a!", "<"))
