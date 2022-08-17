def message_count(events):
    return sum(1 for event in events if event["event_type"] == "message")


def event_count(events):
    return sum(1 for _ in events)  # since events is an iterator we accumulate over it rather than using len()
