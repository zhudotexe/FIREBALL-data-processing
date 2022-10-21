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
        return not previous_state["current"] == current_state["current"]
    previous_combatant_id = previous_state["combatants"][previous_state["current"]]["id"]
    current_combatant_id = current_state["combatants"][current_state["current"]]["id"]
    return not previous_combatant_id == current_combatant_id
