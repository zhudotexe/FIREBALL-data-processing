# group all consecutive automation runs from the same user together
# assign each utterance from each non-DM user to the nearest (in time) automation run group from that user
# assign each utterance from the DM user to the nearest (in time) automation run group, from any user
import collections
import logging
import pathlib

import tqdm.contrib.concurrent
import tqdm.contrib.logging

from heuristics.utils import Event, Instance, MessageGroup
from utils import combat_dir_iterator, get_combat_dirs, write_jsonl

DATA_DIR = pathlib.Path("data/")
OUT_DIR = pathlib.Path("extract/experiment1/")
RUN_PARALLEL = True


def group_utterances_for_user(messages: list[MessageGroup]) -> list[dict[str, list[Event]]]:
    """
    Given all the message-based events for a user, return a list of dicts {before, commands, after},
    clustered based on nearest commands in time.
    """
    triples = collections.defaultdict(lambda: ([], []))  # command -> (before, after)

    non_messages = [g for g in messages if not g.is_only_message()]
    # todo: group all consecutive together

    def nearest_non_message(event):
        nearest_sorted = sorted(non_messages, key=lambda grp: abs(grp.message["timestamp"] - event["timestamp"]))
        if nearest_sorted:
            return nearest_sorted[0]
        return None

    only_messages = [g for g in messages if g.is_only_message()]
    for mgroup in only_messages:
        message = mgroup.message
        nearest_group = nearest_non_message(message)
        if nearest_group is None:
            continue
        if message["timestamp"] < nearest_group.message["timestamp"]:
            triples[nearest_group][0].append(message)
        else:
            triples[nearest_group][1].append(message)

    return [
        {"before": before, "commands": commands.events, "after": after} for commands, (before, after) in triples.items()
    ]


def group_utterances(combat_dir: pathlib.Path):
    inst = Instance(combat_dir_iterator(combat_dir))

    out = []

    message_groups = inst.partitioned_groups(lambda message: message["author_id"])
    for user_id, messages in message_groups:
        out.extend(group_utterances_for_user(messages))

    # discard if we have nothing
    if not out:
        return

    # see what we get
    write_jsonl(OUT_DIR / f"{combat_dir.stem}.jsonl.gz", out)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            tqdm.contrib.concurrent.process_map(group_utterances, get_combat_dirs(DATA_DIR), chunksize=10)
        else:
            for d in tqdm.tqdm(get_combat_dirs(DATA_DIR)):
                group_utterances(d)
