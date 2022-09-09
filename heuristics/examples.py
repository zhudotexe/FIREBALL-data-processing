import json

# hack: filter events to a file instead of returning an instance score
def filter_events_to_file(events) -> float:
    out_file = open("some_file.jsonl")
    for event in events:
        if True:
            out_file.write(json.dumps(event))
            out_file.write("\n")
    out_file.close()
    return 0
