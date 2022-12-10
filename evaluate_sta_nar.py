import pathlib
from evaluate import load
import json
from dataset.utils import read_jsonl_file
import tqdm

RESULTS_FILE = pathlib.Path("results/sta-nar-test-results-ready-for-eval.jsonl")
OUT_DIR = pathlib.Path("results")
PERPLEXITY_MODEL = 'gpt2'

def writeline(f, d):
    f.write(json.dumps(d))
    f.write("\n")


def main():
    perplexity = load("perplexity", module_type="metric")
    bleurt = load("bleurt", module_type="metric")
    bertscore = load("bertscore")
    metrics = [perplexity, bleurt, bertscore]
    predictions = ["full", "nostate", "command_utterance", "dialog_continuation"]
    results = []
    average_results = {(metric.name, prediction): [] for metric in metrics for prediction in predictions}
    results_stream = read_jsonl_file(RESULTS_FILE)
    for data in tqdm.tqdm(results_stream):
        data["perplexity_gold"] = perplexity.compute(predictions=[data['gold']], model_id=PERPLEXITY_MODEL)['perplexities'][0]
        for prediction in predictions:
            pred_str = data[f"prediction_{prediction}"]
            for metric in metrics:
                if metric == perplexity:
                    result = metric.compute(predictions=[pred_str], model_id=PERPLEXITY_MODEL)['perplexities'][0]
                elif metric == bertscore:
                    result = metric.compute(predictions=[pred_str], references=[data['gold']], lang='en')['f1'][0]
                else:
                    result = metric.compute(predictions=[pred_str], references=[data['gold']])['scores'][0]
                data[f"{metric.name}_{prediction}"] = result
                average_results[(metric.name, prediction)].append(result)
        results.append(data)
    with open(OUT_DIR / f"sta-nar-test-results-eval.jsonl", mode="w") as outfile:
        for result in results:
            writeline(outfile, result)
    with open(OUT_DIR / f"sta-nar-test-results-eval-averages.jsonl", mode="w") as outfile:
        for key, value in average_results.items():
            writeline(outfile, {"metric": key[0], "prediction": key[1], "average": sum(value)/len(value)})
    

if __name__ == "__main__":
    main()
                

            