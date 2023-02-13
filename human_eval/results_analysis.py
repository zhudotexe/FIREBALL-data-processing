import csv
import datetime
import enum
import itertools
import pathlib
import re

import numpy as np
from nltk import AnnotationTask
from pydantic import BaseModel
from scipy.stats import kendalltau
from sklearn.metrics import cohen_kappa_score
from sklearn.preprocessing import StandardScaler

RESULTS_PATH = pathlib.Path("results_final.csv")


class ModelEnum(enum.IntEnum):
    HUMAN = 1
    FULL = 2
    NOSTATE = 3
    COMMAND_ONLY = 4
    DIALOG_CONT = 5


class Timer(BaseModel):
    first_click: float
    last_click: float
    page_submit: float
    click_count: int


class ScenarioResponse(BaseModel):
    question_idx: int
    sense: dict[ModelEnum, int]
    specific: dict[ModelEnum, int]
    interesting: dict[ModelEnum, int]
    timer: Timer
    interesting_normalized: dict[ModelEnum, int] = None  # populated after init


class User(BaseModel):
    start_date: datetime.datetime
    end_date: datetime.datetime
    duration: float
    discord_username: str
    discord_id: str
    responses: list[ScenarioResponse]

    @classmethod
    def from_qualtrics_row(cls, d: dict):
        # all the seenN keys that are 1
        scenario_idxs = [int(m.group(1)) for k, v in d.items() if (m := re.match(r"seen(\d+)", k)) and v]
        assert len(scenario_idxs) == 3 or len(scenario_idxs) == 7

        responses = []
        for idx in scenario_idxs:
            sense = {k: d[f"Sense{idx}_{k.value}"] for k in ModelEnum}
            specific = {k: d[f"Specific{idx}_{k.value}"] for k in ModelEnum}
            interesting = {k: d[f"Interesting{idx}_{k.value}"] for k in ModelEnum}
            assert len(sense) == len(specific) == len(interesting) == 5
            timer = Timer(
                first_click=d[f"Timer{idx}_First Click"],
                last_click=d[f"Timer{idx}_Last Click"],
                page_submit=d[f"Timer{idx}_Page Submit"],
                click_count=d[f"Timer{idx}_Click Count"],
            )
            response = ScenarioResponse(
                question_idx=idx,
                sense=sense,
                specific=specific,
                interesting=interesting,
                timer=timer,
            )
            responses.append(response)

        # normalize interest
        all_interest_scores = [[r.interesting[k]] for r in responses for k in ModelEnum]
        assert len(all_interest_scores) == 5 * len(responses)
        scaler = StandardScaler()
        scaler.fit(all_interest_scores)
        # print(f"evaluator {d['QID']} has interest mean {scaler.mean_}")
        for response in responses:
            normalized_interesting = {k: scaler.transform([[response.interesting[k]]])[0, 0] for k in ModelEnum}
            response.interesting_normalized = normalized_interesting

        return cls(
            start_date=d["StartDate"],
            end_date=d["EndDate"],
            duration=d["Duration (in seconds)"],
            discord_username=d["QUsername"],
            discord_id=d["QID"],
            responses=responses,
        )


def load_results():
    with open(RESULTS_PATH, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        # skip 2 qualtrics metadata rows
        next(reader)
        next(reader)
        for row in reader:
            yield User.from_qualtrics_row(row)


def agreement(users, print=print):
    print("\n===== AGREEMENT =====")
    binary_agreements = []
    interesting_agreements = []
    interesting_norm_agreements = []
    for user1, user2 in itertools.combinations(users, 2):
        u1_idxs = {r.question_idx for r in user1.responses}
        u2_idxs = {r.question_idx for r in user2.responses}
        overlap = u1_idxs.intersection(u2_idxs)
        if not overlap:
            continue
        u1_responses = [r for r in user1.responses if r.question_idx in overlap]
        u2_responses = [r for r in user2.responses if r.question_idx in overlap]
        bin_y1 = []
        bin_y2 = []
        interest_y1 = []
        interest_y2 = []
        interest_norm_y1 = []
        interest_norm_y2 = []
        for r1, r2 in zip(u1_responses, u2_responses):
            for model in ModelEnum:
                bin_y1.append(r1.sense[model])
                bin_y2.append(r2.sense[model])
                bin_y1.append(r1.specific[model])
                bin_y2.append(r2.specific[model])
                interest_y1.append(r1.interesting[model])
                interest_y2.append(r2.interesting[model])
                interest_norm_y1.append(r1.interesting_normalized[model])
                interest_norm_y2.append(r2.interesting_normalized[model])

        if bin_y1 == bin_y2:  # sklearn fails on perfect agreement
            binary_agreements.append(1)
        else:
            binary_agreements.append(cohen_kappa_score(bin_y1, bin_y2))
        kt = kendalltau(interest_y1, interest_y2)[0]
        if not np.isnan(kt):
            interesting_agreements.append(kt)
        kt_norm = kendalltau(interest_norm_y1, interest_norm_y2)[0]
        if not np.isnan(kt):
            interesting_norm_agreements.append(kt_norm)
    bin_agreement = np.average(binary_agreements)
    print(f"pairwise Cohen kappa (binary): {bin_agreement:.4f}")
    interest_agreement = np.average(interesting_agreements)
    print(f"Kendall tau (interesting): {interest_agreement:.4f}")
    interest_norm_agreement = np.average(interesting_norm_agreements)
    print(f"Kendall tau (interesting, normalized): {interest_norm_agreement:.4f}")

    # nltk agreement impl
    data = []
    for user in users:
        for r in user.responses:
            for metric in ("sense", "specific"):
                for model in ModelEnum:
                    data.append((user.discord_id, f"{metric}{r.question_idx}_{model.value}", getattr(r, metric)[model]))
    t = AnnotationTask(data)
    alpha = t.alpha()
    print(f"Krippendorf alpha (binary): {alpha:.4f}")

    # statsmodels impl
    # subjects in rows, raters in columns
    # df = pandas.read_csv(RESULTS_PATH, skiprows=(1, 2))
    # data = df.filter(regex=r"(Sense|Specific)\d+_\d+").to_numpy().T
    # agg, cats = aggregate_raters(data)
    # fk = fleiss_kappa(agg[:, :-1])
    # print(f"multirater Fleiss-Kappa: {fk:.4f}")

    # krippendorff impl
    # df = pandas.read_csv(RESULTS_PATH, skiprows=(1, 2))
    # data = df.filter(regex=r"(Sense|Specific)\d+_\d+").to_numpy()
    # print(krippendorff.alpha(data, level_of_measurement="nominal"))

    return bin_agreement, interest_agreement, alpha


def print_completed(users):
    """Prints all the users who completed 3/7, and their min/max/avg question duration"""
    for user in users:
        min_time = min(r.timer.page_submit for r in user.responses)
        max_time = max(r.timer.page_submit for r in user.responses)
        avg_time = np.average([r.timer.page_submit for r in user.responses])
        print(f"{user.discord_username},{user.discord_id},{len(user.responses)},{min_time},{avg_time},{max_time}")


def print_raw(all_responses):
    for model in ModelEnum:
        print(f"{model.name}_sense,{model.name}_specific,{model.name}_interesting,", end="", flush=True)
    print()

    for r in all_responses:
        for model in ModelEnum:
            sense = r.sense[model]
            specific = r.specific[model]
            interesting = r.interesting[model]
            print(f"{sense},{specific},{interesting},", end="", flush=True)
        print()


def main():
    users = list(load_results())
    # averages
    all_responses = [r for user in users for r in user.responses]
    for model in ModelEnum:
        print(f"==== {model.name} ====")
        n_total = len(all_responses)
        avg_sense = np.average([r.sense[model] for r in all_responses])
        n_sense = sum(r.sense[model] for r in all_responses)
        avg_specific = np.average([r.specific[model] for r in all_responses])
        n_specific = sum(r.specific[model] for r in all_responses)
        avg_interesting = np.average([r.interesting[model] for r in all_responses])
        avg_interesting_norm = np.average([r.interesting_normalized[model] for r in all_responses])
        print(f"avg sense: {avg_sense:.2%} ({n_sense}/{n_total})")
        print(f"avg specific: {avg_specific:.2%} ({n_specific}/{n_total})")
        print(f"avg interesting: {avg_interesting:.2f}")
        print(f"avg interesting_norm: {avg_interesting_norm:.2f}")

    bin_agreement, interest_agreement, alpha = agreement(users)
    # print_raw(all_responses)


if __name__ == "__main__":
    main()
