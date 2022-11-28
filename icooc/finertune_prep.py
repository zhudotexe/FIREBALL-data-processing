"""
Fine*r* tuning - taking the finetuned model and giving it one more pass on our data
"""
import csv
import json


def read_train(fp):
    with open(fp, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for idx, utterance, label in reader:
            yield label, utterance


def read_val(fp):
    with open(fp, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for idx, label, utterance in reader:
            yield label, utterance


def csv_to_finetune(reader, outf):
    for label, utterance in reader:
        label = int(float(label))
        if label == 0:
            tok_label = "in-character"
        else:
            tok_label = "out-of-character"
        prompt = f"{utterance}\nlabel:"
        completion = " " + tok_label
        outf.write(json.dumps({"prompt": prompt, "completion": completion}))
        outf.write("\n")


def main():
    with open("ft-icvsooc.jsonl", "w") as outf:
        csv_to_finetune(read_train("icvsooctraining_set.csv"), outf)
    with open("ft-icvsooc-val.jsonl", "w") as valf:
        csv_to_finetune(read_val("icvsoocvalidation_set.csv"), valf)


if __name__ == "__main__":
    main()
    # openai api fine_tunes.create \
    #   -t ft-icvsooc.jsonl \
    #   -v ft-icvsooc-val.jsonl \
    #   -m ada:ft-ccb-lab-members-2022-10-30-01-32-01 \
    #   --compute_classification_metrics \
    #   --classification_n_classes 2 \
    #   --classification_positive_class " in-character" \
    #   --learning_rate_multiplier 0.02 \
    #   --n_epochs 2
