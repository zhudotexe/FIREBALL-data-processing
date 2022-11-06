import glob
import json
import logging
import pathlib

import sklearn.model_selection
import tqdm.contrib.logging

import prompts
from dataset.utils import read_jsonl_file

NORMALIZED_IN_DIR = pathlib.Path("extract/experiment4/")
OUT_DIR = pathlib.Path("extract/")


def _map_to_instance(fp: pathlib.Path, f):
    out = []
    norm_stream = read_jsonl_file(fp)
    for data in norm_stream:
        result = f(data)
        if result:
            out.append(result)
    return out


def _prompt_and_completion(data, prompter, completer) -> dict | None:
    prompt = prompter(data)
    completion = completer(data)
    if not (prompt and completion):
        return
    return {"prompt": prompt, "completion": completion}


def _extract_dict_keys(data, required_keys, keys, **add_data) -> dict | None:
    out = {}
    for key in required_keys:
        r = data[key]
        if not r:
            return
        out[key] = r
    for key in keys:
        out[key] = data[key]
    out.update(add_data)
    return out


def process_utt_cmd_train(fp: pathlib.Path):
    """
    Transforms each normalized datum into a GPT-3 prompt (see prompts.py for the prompt).
    """
    return _map_to_instance(
        fp, lambda data: _prompt_and_completion(data, prompts.utt_cmd_prompt, prompts.utt_cmd_completion)
    )


def process_utt_cmd_test(fp: pathlib.Path):
    """
    Extracts the available keys for this task from the normalized datum.
    X: ("before_utterances", "combat_state_before", "current_actor", "before_idxs")
    y: ("commands_norm",)
    """
    return _map_to_instance(
        fp,
        lambda data: _extract_dict_keys(
            data,
            required_keys=("before_utterances",),
            keys=("combat_state_before", "current_actor", "commands_norm", "speaker_id", "before_idxs"),
            instance_id=fp.stem,
        ),
    )


def process_sta_nar_train(fp: pathlib.Path):
    return _map_to_instance(
        fp, lambda data: _prompt_and_completion(data, prompts.sta_nar_prompt, prompts.sta_nar_completion)
    )


def process_sta_nar_test(fp: pathlib.Path):
    """
    Extracts the available keys for this task from the normalized datum.
    X: ("combat_state_after", "caster_after", "targets_after", "automation_results", "before_idxs", "command_idxs",
        "after_idxs")
    y: ("after_utterances",)
    """
    return _map_to_instance(
        fp,
        lambda data: _extract_dict_keys(
            data,
            required_keys=("after_utterances", "automation_results"),
            keys=(
                "combat_state_after",
                "caster_after",
                "targets_after",
                "speaker_id",
                "before_idxs",
                "command_idxs",
                "after_idxs",
            ),
            instance_id=fp.stem,
        ),
    )


def writeline(f, d):
    f.write(json.dumps(d))
    f.write("\n")


def do_prep(
    paths,
    train_processor,
    test_processor,
    file_name,
    desired_train_pairs=10000,
    desired_test_pairs=10000,
    train_epochs=4,
):
    random_seed = 42
    # split the dataset roughly proportionally to the desired train/test split
    test_frac = desired_test_pairs / (desired_train_pairs + desired_test_pairs)
    paths_train, paths_test = sklearn.model_selection.train_test_split(
        paths, test_size=test_frac, random_state=random_seed
    )

    train = []
    test = []

    trainf = open(OUT_DIR / f"{file_name}-train-{desired_train_pairs}.jsonl", mode="w")
    testf = open(OUT_DIR / f"{file_name}-test-{desired_test_pairs}.jsonl", mode="w")

    for d in tqdm.tqdm(paths_train):
        pairs = train_processor(d)
        train.extend((d, pair) for pair in pairs)

    for d in tqdm.tqdm(paths_test):
        pairs = test_processor(d)
        test.extend((d, pair) for pair in pairs)

    # randomly sample desired number of train/test pairs from disjoint instances
    # then write the rest to restf
    train = sklearn.utils.shuffle(train, random_state=random_seed)
    test = sklearn.utils.shuffle(test, random_state=random_seed)
    train_samples = train[:desired_train_pairs]
    test_samples = test[:desired_test_pairs]
    n_discarded = len(train) - desired_train_pairs + len(test) - desired_test_pairs

    train_insts = set()
    train_chars = 0
    for inst, pair in train_samples:
        writeline(trainf, pair)
        train_insts.add(inst)
        train_chars += len(pair["prompt"]) + len(pair["completion"])

    test_insts = set()
    for inst, pair in test_samples:
        writeline(testf, pair)
        test_insts.add(inst)

    trainf.close()
    testf.close()

    print(
        f"Wrote {file_name} data:\n"
        f"{desired_train_pairs} training pairs from {len(train_insts)} instances\n"
        f"{desired_test_pairs} testing pairs from {len(test_insts)} instances\n"
        f"{n_discarded} pairs discarded"
    )
    train_tokens = train_chars / 4
    davinci_ft_price = 0.03 / 1000
    print(
        f"Estimated Davinci finetune cost ({train_epochs} epochs):"
        f" ${train_tokens * davinci_ft_price * train_epochs:.2f}"
    )


def main(paths: list[pathlib.Path]):
    do_prep(
        paths,
        process_utt_cmd_train,
        process_utt_cmd_test,
        "ft-utt-cmd",
        desired_train_pairs=10000,
        desired_test_pairs=1000,
        train_epochs=2,
    )
    do_prep(
        paths,
        process_sta_nar_train,
        process_sta_nar_test,
        "ft-sta-nar",
        desired_train_pairs=15000,
        desired_test_pairs=1000,
        train_epochs=1,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    filenames = sorted(glob.glob("*.jsonl", root_dir=NORMALIZED_IN_DIR))
    files = [pathlib.Path(NORMALIZED_IN_DIR, fn) for fn in filenames]
    with tqdm.contrib.logging.logging_redirect_tqdm():
        main(files)
    print(f"FT prep complete!")
    print(
        "Now you can run:\n\n"
        "\topenai tools fine_tunes.prepare_data -f extract/<the file you want>\n\n"
        "to prepare a finetune file, then:\n\n"
        '\topenai api fine_tunes.create -t "extract/<that file>_prepared.jsonl" -m ada --n_epochs 1\n\n'
        "to create a finetune. Be careful about your spending "
        "- in order to see more data we lower the number of epochs (see output above)!"
    )
