import glob
import itertools
import logging
import pathlib
import re
import sys

import tqdm.contrib.concurrent
import tqdm.contrib.logging

sys.path.append("..")

from dataset.utils import combat_dir_iterator, read_gzipped_file
from heuristics.utils import Instance

DATA_DIR = pathlib.Path("../data/")
IN_DIR = pathlib.Path("../extract/experiment3/")
RUN_PARALLEL = True
log = logging.getLogger("tuppertest")
loglevel = logging.CRITICAL

TUPPER_REGEX = re.compile(r"\w{1,10}[:.;]")  # e.g. N:text or DM;text or Name.text


class Distill4Inst(Instance):
    def process_triple(self, triple: dict):
        """Given a triple, return a processed triple - main entrypoint"""
        messages_replaced_regex = 0
        messages_replaced_greedy = 0
        before = triple["before"]
        after = triple["after"]
        for msg in itertools.chain(before, after):
            content = msg["content"]
            msg_idx = self.events.index(msg)
            # remove any Tupper prefixes
            # has_tupper = TUPPER_REGEX.match(content)
            # if has_tupper:
            #     similar_message = self.find(
            #         lambda e: e["event_type"] == "message"
            #         and e["author_id"] != msg["author_id"]
            #         and e["content"] in content
            #         and e["content"]
            #         and e.get("author_bot", True),
            #         after=msg_idx,
            #         before=msg_idx + 16,
            #     )
            #     if similar_message is not None:
            #         similar_content = similar_message["content"]
            #         log.info(
            #             f"REGEX: Replaced message content with tupper content:\n{content!r}\n---\n{similar_content!r}\n"
            #         )
            #         messages_replaced_regex += 1
            #     else:
            #         log.warning(f"REGEX: Could not find tupper content for tupper message {content!r}")

            # really try and get rid of tupper
            similar_message = self.find(
                lambda e: e["event_type"] == "message"
                and e["author_id"] != msg["author_id"]
                and e["content"] in content
                and e["content"]
                and e.get("author_bot", True),
                after=msg_idx,
                before=msg_idx + 16,
            )
            if similar_message is not None:
                similar_content = similar_message["content"]
                # the new content must be at least 80% of the old
                if 0.7 < len(similar_content) / len(content) < 1:
                    log.info(
                        f"GREEDY: Replaced message content with tupper content:\n{content!r}\n---\n{similar_content!r}\n"
                    )
                    messages_replaced_greedy += 1
                elif len(similar_content.split()) > 1:
                    log.warning(
                        f"GREEDY: Found similar message but ratio is weird:\n{content!r}\n---\n{similar_content!r}\n"
                    )
        return messages_replaced_regex, messages_replaced_greedy


def process_file(fp: pathlib.Path):
    triple_stream = read_gzipped_file(fp)
    combat_id, *_ = fp.stem.split(".")
    event_stream = combat_dir_iterator(DATA_DIR / combat_id)
    inst = Distill4Inst(event_stream)

    messages_replaced_regex = 0
    messages_replaced_greedy = 0
    messages_total = 0
    for triple in triple_stream:
        messages_total += len(triple["before"]) + len(triple["after"])
        regex, greedy = inst.process_triple(triple)
        messages_replaced_regex += regex
        messages_replaced_greedy += greedy
    return messages_replaced_regex, messages_replaced_greedy, messages_total


if __name__ == "__main__":
    logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
    filenames = sorted(glob.glob("*.gz", root_dir=IN_DIR))
    files = [pathlib.Path(IN_DIR, fn) for fn in filenames]
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            results = tqdm.contrib.concurrent.process_map(process_file, files, chunksize=10)
        else:
            results = []
            for d in tqdm.tqdm(files):
                results.append(process_file(d))
        print(f"regex: {sum(x for x, _, _ in results)}")
        print(f"greedy: {sum(x for _, x, _ in results)}")
        print(f"total: {sum(x for _, _, x in results)}")
