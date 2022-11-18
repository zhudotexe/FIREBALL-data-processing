"""
Distill3: Given triples, filter the events in the triples:
- remove OOC utterances

Input: {"before": [Message...], "commands": [Event...], "after": [Message...]}

Output: {
    "before": [Message...],
    "commands": [Event...],
    "after": [Message...],
}
- with `after` filtered to only include IC-classified utterances (maybe `before` too - see how you feel about it)
"""
import glob
import logging
import pathlib

import torch
import tqdm.contrib.concurrent
import tqdm.contrib.logging
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

from dataset.utils import read_gzipped_file, write_jsonl

DATA_DIR = pathlib.Path("data/")
# IN_DIR = pathlib.Path("extract/experiment2/")
# OUT_DIR = pathlib.Path("extract/experiment3/")
IN_DIR = pathlib.Path("extract/regression/experiment3a/")
OUT_DIR = pathlib.Path("extract/regression/experiment3b/")
MODEL_DIR = pathlib.Path("models/ic_ooc_1-finetuned/checkpoint-9500")

log = logging.getLogger("distill3")
loglevel = logging.INFO


def process_triple(triple, classifier) -> dict | None:
    after = triple["after"]
    text_samples = [event["content"].strip() for event in after]
    tokenizer_kwargs = {"padding": True, "truncation": True}
    predictions = classifier(text_samples, **tokenizer_kwargs)
    # IC  = 1, OOC = 0 labels
    filtered_utterances = [event for event, prediction in zip(after, predictions) if prediction["label"] == "LABEL_1"]
    triple["after"] = filtered_utterances
    log.debug(triple.keys())
    log.info(f'after content: {sum(len(msg["content"]) for msg in triple["after"])} in {len(triple["after"])} events')
    if triple["after"] or triple["before"]:
        return triple
    return None


def process_file(fp: pathlib.Path, classifier):
    """
    Given a path to a file containing a list of triples, filter the triples and return a pair of
    (n_triples_in, n_triples_out).
    """
    triple_stream = read_gzipped_file(fp)
    num_triples_in = 0
    combat_id, *_ = fp.stem.split(".")
    out = []

    for triple in triple_stream:
        num_triples_in += 1
        processed = process_triple(triple, classifier)
        if processed is not None:
            out.append(processed)

    # discard if we have nothing
    if not out:
        log.info("nothing was processed")
        return num_triples_in, 0

    # see what we get
    write_jsonl(OUT_DIR / f"{combat_id}.jsonl.gz", out)
    return num_triples_in, len(out)


if __name__ == "__main__":
    logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
    log.info(f"cuda {torch.cuda.is_available()}")
    device = 0 if torch.cuda.is_available() else -1
    log.info(f"device: {device}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filenames = sorted(glob.glob("*.gz", root_dir=IN_DIR))
    files = [pathlib.Path(IN_DIR, fn) for fn in filenames]
    log.info(f"files {len(files)}")
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    classifier = pipeline("text-classification", model=model, tokenizer=tokenizer, device=device)
    log.info("classifier constructed")
    with tqdm.contrib.logging.logging_redirect_tqdm():
        results = []
        for d in tqdm.tqdm(files):
            results.append(process_file(d, classifier))

    kept_distill_count = sum(1 for (i, o) in results if o)
    n_triples_in = sum(i for i, o in results)
    n_triples_out = sum(o for i, o in results)
    print(
        f"Distill complete!\n"
        f"Instances: {len(filenames)} -> {kept_distill_count}\n"
        f"Triples: {n_triples_in} -> {n_triples_out}"
    )
