import glob
import json
import logging
import pathlib

import tqdm.contrib.logging

from dataset.utils import read_jsonl_file

OUT_UTT_TO_CMD_FILE = pathlib.Path("extract/ft-utt-cmd.jsonl")
OUT_STA_TO_NAR_FILE = pathlib.Path("extract/ft-sta-nar.jsonl")
OUT_UTT_TO_NAR_FILE = pathlib.Path("extract/ft-utt-nar.jsonl")
NORMALIZED_IN_DIR = pathlib.Path("extract/experiment4/")

SEP = "\n<|asep|>\n"
COMMAND_SEP = "\n<|csep|>\n"
STOP_SEQ = "\n<|aeot|>"


def process_file(fp: pathlib.Path) -> tuple[list, list, list]:
    utt_cmd = []
    sta_nar = []
    utt_nar = []
    triple_stream = read_jsonl_file(fp)
    for triple in triple_stream:
        before = triple["before_utterances"]
        commands = triple["commands_norm"]
        after = triple["after_utterances"]

        if before:
            prompt = "\n".join(before) + SEP
            completion = COMMAND_SEP.join(commands) + STOP_SEQ
            utt_cmd.append({"prompt": prompt, "completion": completion})

        if after:
            prompt = COMMAND_SEP.join(commands) + SEP
            completion = "\n".join(after) + STOP_SEQ
            sta_nar.append({"prompt": prompt, "completion": completion})

        if before and after:
            prompt = "\n".join(before) + SEP
            completion = "\n".join(after) + STOP_SEQ
            utt_nar.append({"prompt": prompt, "completion": completion})

    return utt_cmd, sta_nar, utt_nar


def writelines(f, dicts):
    for d in dicts:
        f.write(json.dumps(d))
        f.write("\n")


def main(paths: list[pathlib.Path]):
    f_utt_cmd = open(OUT_UTT_TO_CMD_FILE, mode="w")
    f_sta_nar = open(OUT_STA_TO_NAR_FILE, mode="w")
    f_utt_nar = open(OUT_UTT_TO_NAR_FILE, mode="w")
    with tqdm.contrib.logging.logging_redirect_tqdm():
        for d in tqdm.tqdm(paths):
            utt_cmd, sta_nar, utt_nar = process_file(d)
            writelines(f_utt_cmd, utt_cmd)
            writelines(f_sta_nar, sta_nar)
            writelines(f_utt_nar, utt_nar)
    f_utt_cmd.close()
    f_sta_nar.close()
    f_utt_nar.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    filenames = sorted(glob.glob("*.jsonl", root_dir=NORMALIZED_IN_DIR))
    files = [pathlib.Path(NORMALIZED_IN_DIR, fn) for fn in filenames]
    main(files)
    print(f"FT prep complete!")
    print(
        "Now you can run:\n\n"
        "\topenai tools fine_tunes.prepare_data -f extract/<the file you want>\n\n"
        "to prepare a finetune file, then:\n\n"
        '\topenai api fine_tunes.create -t "extract/<that file>_prepared.jsonl" -m ada\n\n'
        "to create a finetune. Be careful about your spending!"
    )
