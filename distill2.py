"""
Input: {"before": [Message...], "commands": [Event...], "after": [Message...]}

Output: {
    "before": [Message...],
    "before_utterances": [str...],
    "commands": [Event...],
    "commands_norm": [str...],
    "after": [Message...],
    "after_utterances": [str...],
}
- with `before` and `after` filtered to only include utterances from the user who ran `commands` or a DM
"""
import glob
import logging
import pathlib

import tqdm.contrib.concurrent
import tqdm.contrib.logging

from heuristics.utils import Instance, MessageGroup
from utils import combat_dir_iterator, read_gzipped_file, write_jsonl

DATA_DIR = pathlib.Path("data/")
IN_DIR = pathlib.Path("extract/experiment1/")
OUT_DIR = pathlib.Path("extract/experiment2/")
RUN_PARALLEL = True


def extract_dms_from_events(inst: Instance) -> set[str]:
    """Given events, return a set of user IDs who were DMs at any point during the combat."""
    out = set()
    for event in inst.find_all(lambda e: e["event_type"] == "combat_state_update"):
        out.add(str(event["data"]["dm"]))
    return out


def normalize_command_group(group: MessageGroup) -> str | None:
    command = group.find_event_of_type("command")
    if command is None:
        return None
    # use post-alias content
    content: str = command["content"]

    # normalize prefix
    content = content.replace(command["prefix"], "!", 1)

    # normalize snippets
    # TODO: import avrae and use argsplit
    content_words = content.split()
    for snippet_resolution in group.find_all_of_type("snippet_resolution"):
        for idx, word in enumerate(content_words):
            if word == snippet_resolution["snippet_name"]:
                content_words[idx] = snippet_resolution["content_after"]
                break
    content = " ".join(content_words)

    # TODO: we can probably rebuild cast/attack invocations by importing avrae
    # lets us reference exact action/attack/spell names
    return content


def process_triple(triple: dict, dms) -> dict | None:
    """Given a triple, return a processed triple"""
    before = triple["before"]
    commands = triple["commands"]
    after = triple["after"]
    command_author = commands[0]["author_id"]

    # normalize utterances
    author_filter = lambda msg: msg["author_id"] == command_author or msg["author_id"] in dms
    before = list(filter(author_filter, before))
    before_utterances = [msg["content"] for msg in before]
    after = list(filter(author_filter, after))
    after_utterances = [msg["content"] for msg in after]

    # normalize commands
    commands_grouped = Instance(commands).message_groups
    assert sum(len(g) for g in commands_grouped) == len(commands)
    commands_norm = []
    for g in commands_grouped:
        norm = normalize_command_group(g)
        if norm:
            commands_norm.append(norm)

    # TODO: stringify automation run for GPT-3
    # TODO: stringify caster attributes for GPT-3

    # discard if we have no filtered utterances
    if not (before or after):
        return None

    return {
        # "before": before,
        "before_utterances": before_utterances,
        # "commands": commands,
        "commands_norm": commands_norm,
        # "after": after,
        "after_utterances": after_utterances,
    }


def process_file(fp: pathlib.Path):
    triple_stream = read_gzipped_file(fp)
    combat_id, *_ = fp.stem.split(".")
    event_stream = combat_dir_iterator(DATA_DIR / combat_id)
    inst = Instance(event_stream)
    dms = extract_dms_from_events(inst)
    out = []

    for triple in triple_stream:
        processed = process_triple(triple, dms)
        if processed is not None:
            out.append(processed)

    # discard if we have nothing
    if not out:
        return

    # see what we get
    write_jsonl(OUT_DIR / f"{combat_id}.jsonl", out)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filenames = sorted(glob.glob("*.gz", root_dir=IN_DIR))
    files = [pathlib.Path(IN_DIR, fn) for fn in filenames]
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            tqdm.contrib.concurrent.process_map(process_file, files, chunksize=10)
        else:
            for d in tqdm.tqdm(files):
                process_file(d)
