"""
Extract all utterances from the previously extracted (RP, command, state) and (command, state, narration) tuples.
Depends on extract_rp_and_commands.py and extract_state_and_narration.py.
"""
import csv
import pathlib

import utils

RP_EXTRACT_DIR = pathlib.Path("extract/rp/")
NARR_EXTRACT_DIR = pathlib.Path("extract/narration/")
OUTPUT_FILE = pathlib.Path("extract/all_utterances.csv")


class UtteranceWriter:
    def __init__(self, outpath):
        self.outfile = open(outpath, "w")
        self.csvwriter = csv.DictWriter(
            self.outfile,
            fieldnames=[
                "message_id",
                "author_id",
                "author_name",
                "author_bot",
                "created_at",
                "referenced_message_id",
                "content",
            ],
            extrasaction="ignore",
        )
        self.csvwriter.writeheader()

    def write_message(self, message):
        self.csvwriter.writerow(message)

    def close(self):
        self.outfile.close()


def main():
    writer = UtteranceWriter(OUTPUT_FILE)

    for rp_tuple in utils.combat_dir_iterator(RP_EXTRACT_DIR):
        for utterance in rp_tuple["utterances"]:
            writer.write_message(utterance)

    for narration_tuple in utils.combat_dir_iterator(NARR_EXTRACT_DIR):
        for utterance in narration_tuple["utterances"]:
            writer.write_message(utterance)

    writer.close()


if __name__ == "__main__":
    main()
