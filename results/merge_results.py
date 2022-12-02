import json
import pathlib
import sys

import tqdm

sys.path.append("..")

import prompts
from dataset.utils import combat_dir_iterator, read_jsonl_file
from distill4_normalize import Distill4Inst

DATA_DIR = pathlib.Path("../data/")

# utt->cmd
UTT_CMD_CANONICAL = pathlib.Path("../extract/ft-utt-cmd-test-1000.jsonl")
UTT_CMD_FULL = pathlib.Path("utt-cmd-test-predictions-full.jsonl")
UTT_CMD_NOSTATE = pathlib.Path("utt-cmd-test-predictions-nostate.jsonl")
UTT_CMD_FEWSHOT = pathlib.Path("utt-cmd-text-3-shot-test-predictions.jsonl")
UTT_CMD_MERGED = pathlib.Path("utt-cmd-test-results-ready-for-eval.jsonl")
UTT_CMD_KEYS = (
    "before_utterances",
    "combat_state_before",
    "current_actor",
    "commands_norm",
    "speaker_id",
    "before_idxs",
    "before_state_idx",
)

# sta->nar
STA_NAR_CANONICAL = pathlib.Path("../extract/ft-sta-nar-test-1000.jsonl")
STA_NAR_FULL = pathlib.Path("sta-nar-test-predictions-full.jsonl")
STA_NAR_NOSTATE = pathlib.Path("sta-nar-test-predictions-state-ablation.jsonl")
STA_NAR_COMMAND_UTTERANCE = pathlib.Path("sta-nar-test-predictions-command-utterance.jsonl")
STA_NAR_DIALOG_CONTINUATION = pathlib.Path("sta-nar-test-predictions-dialog-continuation.jsonl")
STA_NAR_MERGED = pathlib.Path("sta-nar-test-results-ready-for-eval.jsonl")
STA_NAR_KEYS = (
    "after_utterances",
    "automation_results",
    "commands_norm",
    "combat_state_after",
    "caster_after",
    "targets_after",
    "speaker_id",
    "before_idxs",
    "before_state_idx",
    "command_idxs",
    "after_state_idx",
    "after_idxs",
    "embed_idxs",
    "utterance_history",
)


class UttCmdInst(Distill4Inst):
    pass


def merge_utt_cmd():
    test_data = list(read_jsonl_file(UTT_CMD_CANONICAL))

    def find_canonical_datum_for(predicted_datum):
        for datum in test_data:
            if all(datum[k] == predicted_datum[k] for k in UTT_CMD_KEYS):
                return datum
        raise RuntimeError("couldn't find canonical, do you have the right version of ft-utt-cmd-test-1000.jsonl?")

    # merge the predictions
    for predicted_datum in read_jsonl_file(UTT_CMD_FULL):
        canonical_datum = find_canonical_datum_for(predicted_datum)
        canonical_datum["prediction_full"] = predicted_datum["prediction_full"]

    for predicted_datum in read_jsonl_file(UTT_CMD_NOSTATE):
        canonical_datum = find_canonical_datum_for(predicted_datum)
        canonical_datum["prediction_nostate"] = predicted_datum["prediction_nostate"]

    for predicted_datum in read_jsonl_file(UTT_CMD_FEWSHOT):
        canonical_datum = find_canonical_datum_for(predicted_datum)
        canonical_datum["prediction_fewshot_full"] = predicted_datum["prediction_full"]
        canonical_datum["prediction_fewshot_nostate"] = predicted_datum["prediction_nostate"]

    # generate the gold label, skipping any instances that don't have all the expected keys
    # also go back to the data and find the combat state and characters for pass@K testing
    final_merged = []
    keys = ("prediction_full", "prediction_nostate", "prediction_fewshot_full", "prediction_fewshot_nostate")
    for d in tqdm.tqdm(test_data):
        if not all(k in d for k in keys):
            print("missing some predictions, skipping")
            continue
        event_stream = combat_dir_iterator(DATA_DIR / d["instance_id"])
        inst = UttCmdInst(event_stream)
        combat_state = inst.events[d["before_state_idx"]]["data"]
        inst.extract_characters_backward(inst.events[d["before_state_idx"]])
        inst.extract_characters_forward(inst.events[d["before_state_idx"]])
        characters = [c.to_dict() for c in inst.characters.values()]
        out = {
            "gold": prompts.utt_cmd_completion(d, include_sep=False),
            **{k: d[k] for k in keys},
            "combat_state": combat_state,
            "characters": characters,
        }
        final_merged.append(out)

    with open(UTT_CMD_MERGED, mode="w") as f:
        for d in final_merged:
            f.write(json.dumps(d))
            f.write("\n")


def merge_sta_nar():
    test_data = list(read_jsonl_file(STA_NAR_CANONICAL))

    def find_canonical_datum_for(predicted_datum):
        for datum in test_data:
            if all(datum[k] == predicted_datum[k] for k in STA_NAR_KEYS):
                return datum
        raise RuntimeError("couldn't find canonical, do you have the right version of ft-sta-nar-test-1000.jsonl?")

    # merge the predictions
    for predicted_datum in read_jsonl_file(STA_NAR_FULL):
        canonical_datum = find_canonical_datum_for(predicted_datum)
        canonical_datum["prediction_full"] = predicted_datum["prediction_full"]

    for predicted_datum in read_jsonl_file(STA_NAR_NOSTATE):
        canonical_datum = find_canonical_datum_for(predicted_datum)
        canonical_datum["prediction_nostate"] = predicted_datum["prediction_state-ablation"]

    for predicted_datum in read_jsonl_file(STA_NAR_COMMAND_UTTERANCE):
        canonical_datum = find_canonical_datum_for(predicted_datum)
        canonical_datum["prediction_command_utterance"] = predicted_datum["prediction_command-utterance"]

    for predicted_datum in read_jsonl_file(STA_NAR_DIALOG_CONTINUATION):
        canonical_datum = find_canonical_datum_for(predicted_datum)
        canonical_datum["prediction_dialog_continuation"] = predicted_datum["prediction_dialog-continuation"]

    # generate the gold label, skipping any instances that don't have all the expected keys
    final_merged = []
    keys = (
        "prediction_full",
        "prediction_nostate",
        "prediction_command_utterance",
        "prediction_dialog_continuation",
    )
    for d in test_data:
        if not all(k in d for k in keys):
            print("missing some predictions, skipping")
            continue
        out = {
            "gold": prompts.sta_nar_completion(d, include_sep=False),
            **{k: d[k] for k in keys},
        }
        final_merged.append(out)

    with open(STA_NAR_MERGED, mode="w") as f:
        for d in final_merged:
            f.write(json.dumps(d))
            f.write("\n")


if __name__ == "__main__":
    #merge_utt_cmd()
    merge_sta_nar()
