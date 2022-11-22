import csv
import logging
import time

import openai

log = logging.getLogger("icooc")
loglevel = logging.INFO
logging.getLogger("openai").setLevel(logging.WARNING)


def get_ooc_ic_label(text, finetuned_model="ada:ft-ccb-lab-members-2022-10-30-01-32-01", wait_time=0.05):
    if not text:
        return "out-of-character"
    if "OOC" in text or "OOG" in text or text.startswith("("):
        return "out-of-character"
    #  if text.startswith('"'):
    #  	return "in-character"
    if len(text.split(" ")) > 200:
        text = " ".join(text.split(" ")[:200])
    for _ in range(3):
        response = openai.Completion.create(
            model=finetuned_model,
            prompt=text + "\nlabel: ",
            temperature=0.7,
            max_tokens=7,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=["###", "\n"],
        )
        time.sleep(wait_time)
        label = response["choices"][0]["text"].strip()
        if label == "in-character" or label == "out-of-character" or label == "mixed":
            return label
    return None


def main():
    labels = []
    predictions = []
    with open("icvsoocvalidation_set.csv", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for idx, label, utterance in reader:
            print(utterance)
            prediction = get_ooc_ic_label(utterance)
            labels.append(int(float(label)))
            print(prediction, int(float(label)))
            print()
            if prediction == "in-character":
                predictions.append(0)
            else:
                predictions.append(1)

    with open("icvsoocvalidation_results.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("label", "prediction"))
        writer.writerows(zip(labels, predictions))


if __name__ == "__main__":
    main()
