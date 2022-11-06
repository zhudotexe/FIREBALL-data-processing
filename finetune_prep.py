"""
Input:
{
    "before_utterances": before_utterances,     # list of str
    "combat_state_before": actor_list_before,   # list of actors
    "commands_norm": commands_norm,             # list of str
    "automation_results": automation_norm,      # list of str
    "caster_after": caster_norm,                # actor
    "targets_after": targets,                   # list of actors
    "combat_state_after": actor_list_after,     # list of actors
    "after_utterances": after_utterances,       # list of str
}
"""
import glob
import json
import logging
import pathlib

import sklearn.model_selection
import tqdm.contrib.logging

from dataset.utils import read_jsonl_file

NORMALIZED_IN_DIR = pathlib.Path("extract/experiment4/")
OUT_DIR = pathlib.Path("extract/")

SEP = "\n<|asep|>\n"
COMMAND_SEP = "\n<|csep|>\n"
STOP_SEQ = "\n<|aeot|>"


def stringify_actor(actor: dict):
    # Name (Race/creature type; class if available) <X/Y HP> [Effects]
    short_parts = [actor["name"]]
    # Description: ...
    #
    # ---
    # Name: NAME
    # Class:
    # Race:
    # Attacks:
    # Spells:
    # Actions:
    # Effects:
    long_parts = []

    # short parts
    race_and_class_parts = []
    if actor["race"]:
        race_and_class_parts.append(actor["race"])
    if actor["class"]:
        race_and_class_parts.append(actor["class"])
    race_and_class = "; ".join(race_and_class_parts)

    if race_and_class:
        short_parts.append(f"({race_and_class})")
    short_parts.append(actor["hp"])
    if actor["effects"]:
        short_parts.append(f"[{actor['effects']}]")

    # long parts
    if actor["description"]:
        long_parts.append(f"Description: {actor['description']}\n---")
    long_parts.append(f"Name: {actor['name']}")
    if actor["class"]:
        long_parts.append(f"Class: {actor['class']}")
    if actor["race"]:
        long_parts.append(f"Race: {actor['race']}")
    if actor["attacks"]:
        long_parts.append(f"Attacks: {actor['attacks']}")
    if actor["spells"]:
        long_parts.append(f"Spells: {actor['spells']}")
    if actor["actions"]:
        long_parts.append(f"Actions: {actor['actions']}")
    if actor["effects"]:
        long_parts.append(f"Effects: {actor['effects']}")

    return {"short": " ".join(short_parts), "long": "\n".join(long_parts)}


def process_utt_cmd(fp: pathlib.Path):
    out = []
    norm_stream = read_jsonl_file(fp)
    for data in norm_stream:
        before = data["before_utterances"]
        state_before = data["combat_state_before"]
        current_actor_name = data["current_turn"]
        commands = data["commands_norm"]
        caster_name = data["caster_after"]["name"]
        target_names = [t["name"] for t in data["targets_after"]]

        # if no before utterances, skip
        if not before:
            continue

        # find caster and target in before-states
        actors_by_name = {a["name"]: a for a in state_before}
        try:
            caster = actors_by_name[caster_name]
            targets = [actors_by_name[target_name] for target_name in target_names]
        except KeyError:
            continue

        # prompt:
        # Actors:
        # - Name (Race/creature type; class if available) <X/Y HP> [Effects]
        # - ...
        # Current: Name
        #
        # Targets:
        # - Name (Race/creature type; class if available) <X/Y HP>
        # - ...
        #
        # Description: ...
        #
        # ---
        # Name: NAME
        # Class:
        # Race:
        # Attacks:
        # Spells:
        # Actions:
        # Effects:
        #
        # RP
        # <|asep|>
        # command
        # <|aeot|>
        prompt_parts = []

        actors = [f"- {stringify_actor(a)['short']}" for a in state_before]
        actors_prompt = f"Actors:\n" + "\n".join(actors)
        if actors:
            prompt_parts.append(actors_prompt)
        prompt_parts.append(str(current_actor_name))

        targets_str = [f"- {stringify_actor(a)['short']}" for a in targets]
        targets_prompt = f"Targets:\n" + "\n".join(targets_str)
        if targets:
            prompt_parts.append(targets_prompt)

        prompt_parts.append(stringify_actor(caster)["long"])

        rp = "\n".join(before)
        prompt_parts.append(rp)

        # TODO: run ablation by removing parts of the prompt

        prompt = "\n\n".join(prompt_parts) + SEP
        completion = COMMAND_SEP.join(commands) + STOP_SEQ
        out.append({"prompt": prompt, "completion": completion})

    return out


def process_sta_nar(fp: pathlib.Path):
    out = []
    norm_stream = read_jsonl_file(fp)
    for data in norm_stream:
        after = data["after_utterances"]
        state_after = data["combat_state_after"]
        caster = data["caster_after"]
        targets = data["targets_after"]
        automation_results = data["automation_results"]

        # skip if no after utterances
        if not after:
            continue

        # prompt:
        # Actors: (state after)
        # - Name (Race/creature type; class if available) <X/Y HP> [Effects]
        # - ...
        #
        # Targets: (pulled from after)
        # - Name (Race/creature type; class if available) <X/Y HP>
        # - ...
        #
        # Description: ... (pulled from after)
        #
        # ---
        # Name: NAME
        # Class:
        # Race:
        # Attacks:
        # Spells:
        # Actions:
        # Effects:
        #
        # AUTOMATION_STRINGIFY
        # <|asep|>
        # after
        # <|aeot|>

        prompt_parts = []

        actors = [f"- {stringify_actor(a)['short']}" for a in state_after]
        actors_prompt = f"Actors:\n" + "\n".join(actors)
        if actors:
            prompt_parts.append(actors_prompt)

        targets_str = [f"- {stringify_actor(a)['short']}" for a in targets]
        targets_prompt = f"Targets:\n" + "\n".join(targets_str)
        if targets:
            prompt_parts.append(targets_prompt)

        prompt_parts.append(stringify_actor(caster)["long"])

        prompt_parts.append("\n".join(automation_results))

        # TODO: run ablation by removing parts of the prompt

        prompt = "\n\n".join(prompt_parts) + SEP
        completion = "\n".join(after) + STOP_SEQ
        out.append({"prompt": prompt, "completion": completion})

    return out


def writeline(f, d):
    f.write(json.dumps(d))
    f.write("\n")


def do_prep(paths, processor, file_name, desired_train_pairs=10000, desired_test_pairs=10000, train_epochs=4):
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
    restf = open(OUT_DIR / f"{file_name}-rest.jsonl", mode="w")

    for d in tqdm.tqdm(paths_train):
        pairs = processor(d)
        train.extend((d, pair) for pair in pairs)

    for d in tqdm.tqdm(paths_test):
        pairs = processor(d)
        test.extend((d, pair) for pair in pairs)

    # randomly sample desired number of train/test pairs from disjoint instances
    # then write the rest to restf
    train = sklearn.utils.shuffle(train, random_state=random_seed)
    test = sklearn.utils.shuffle(test, random_state=random_seed)
    train_samples, train_rest = train[:desired_train_pairs], train[desired_train_pairs:]
    test_samples, test_rest = test[:desired_test_pairs], test[desired_test_pairs:]
    rest = train_rest + test_rest

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

    for inst, pair in rest:
        writeline(restf, pair)

    print(
        f"Wrote {file_name} data:\n"
        f"{desired_train_pairs} training pairs from {len(train_insts)} instances\n"
        f"{desired_test_pairs} testing pairs from {len(test_insts)} instances\n"
        f"{len(rest)} other pairs"
    )
    train_tokens = train_chars / 4
    davinci_ft_price = 0.03 / 1000
    print(
        f"Estimated Davinci finetune cost ({train_epochs} epochs):"
        f" ${train_tokens * davinci_ft_price * train_epochs:.2f}"
    )


def main(paths: list[pathlib.Path]):
    do_prep(paths, process_utt_cmd, "ft-utt-cmd", desired_train_pairs=10000, desired_test_pairs=1000, train_epochs=2)
    do_prep(paths, process_sta_nar, "ft-sta-nar", desired_train_pairs=15000, desired_test_pairs=1000, train_epochs=1)


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
        "to create a finetune. Be careful about your spending- in order to see more data we lower the number of epochs!"
    )
