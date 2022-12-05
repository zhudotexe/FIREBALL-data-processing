"""
Helper script that turns on answer randomization for each RO question in an exported survey.
"""
import json
import pathlib

fp = pathlib.Path("/Users/andrew/Downloads/FIREBALL_Human_Eval.qsf")
outp = pathlib.Path("/Users/andrew/Downloads/export.qsf")
with open(fp) as f:
    data = json.load(f)

for elem in data["SurveyElements"]:
    if elem["Element"] == "SQ" and elem["Payload"]["QuestionType"] == "RO":
        elem["Payload"]["Randomization"] = {"Advanced": None, "Type": "All", "TotalRandSubset": ""}

with open(outp, "w") as f:
    json.dump(data, f)
