"""
Helper script that turns all the rank questions into matrix/slider questions, because ranking is hard to analyze
"""

import json
import pathlib

from prep_human_eval import INTERESTING_INSTRUCTIONS, SENSE_INSTRUCTIONS, SPECIFIC_INSTRUCTIONS

fp = pathlib.Path("FIREBALL_Human_Eval.qsf")
outp = pathlib.Path("FIREBALL_Human_Eval_fix.qsf")
with open(fp) as f:
    data = json.load(f)

for elem in data["SurveyElements"]:
    # for each rankorder:
    if elem["Element"] == "SQ" and elem["Payload"]["QuestionType"] == "RO":
        payload = elem["Payload"]
        # SenseN
        # replace SenseN and SpecificN instructions
        if payload["DataExportTag"].startswith("Sense"):
            payload["QuestionText"] = SENSE_INSTRUCTIONS
            payload["QuestionType"] = "Matrix"
            payload["Selector"] = "Likert"
            payload["SubSelector"] = "SingleAnswer"
            payload["Validation"] = {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}
            payload["Answers"] = {
                "1": {"Display": "Yes", "ExclusiveAnswer": True},
                "2": {"Display": "No", "ExclusiveAnswer": True},
            }
            payload["AnswerOrder"] = [1, 2]
            payload["RecodeValues"] = {"1": "1", "2": "0"}
            payload["Configuration"] = {
                "QuestionDescriptionOption": "UseText",
                "TextPosition": "inline",
                "ChoiceColumnWidth": 25,
                "Stack": "OFF",
                "WhiteSpace": "OFF",
                "MobileFirst": True,
            }
        # SpecificN
        elif payload["DataExportTag"].startswith("Specific"):
            payload["QuestionText"] = SPECIFIC_INSTRUCTIONS
            payload["QuestionType"] = "Matrix"
            payload["Selector"] = "Likert"
            payload["SubSelector"] = "SingleAnswer"
            payload["Validation"] = {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}
            payload["Answers"] = {
                "1": {"Display": "Yes", "ExclusiveAnswer": True},
                "2": {"Display": "No", "ExclusiveAnswer": True},
            }
            payload["AnswerOrder"] = [1, 2]
            payload["RecodeValues"] = {"1": "1", "2": "0"}
            payload["Configuration"] = {
                "QuestionDescriptionOption": "UseText",
                "TextPosition": "inline",
                "ChoiceColumnWidth": 25,
                "Stack": "OFF",
                "WhiteSpace": "OFF",
                "MobileFirst": True,
            }
        # InterestingN
        elif payload["DataExportTag"].startswith("Interesting"):
            payload["QuestionText"] = INTERESTING_INSTRUCTIONS
            payload["QuestionType"] = "Slider"
            payload["Selector"] = "HSLIDER"
            payload.pop("SubSelector")
            payload["Validation"] = {"Settings": {"ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None"}}
            payload["Labels"] = {"1": {"Display": "Less Interesting"}, "2": {"Display": "More Interesting"}}
            payload["Answers"] = {
                "1": {"Display": 1},
                "2": {"Display": 2},
                "3": {"Display": 3},
                "4": {"Display": 4},
                "5": {"Display": 5},
                "6": {"Display": 6},
                "7": {"Display": 7},
                "8": {"Display": 8},
                "9": {"Display": 9},
                "10": {"Display": 10},
            }
            payload["Configuration"] = {
                "QuestionDescriptionOption": "UseText",
                "TextPosition": "inline",
                "CSSliderMin": 1,
                "CSSliderMax": 10,
                "GridLines": 9,
                "NumDecimals": "0",
                "ShowValue": True,
                "SliderStartPositions": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
                "SnapToGrid": True,
                "CustomStart": True,
                "NotApplicable": False,
                "MobileFirst": True,
            }
        else:
            raise RuntimeError
        elem["Payload"]["Randomization"] = {"Advanced": None, "Type": "All", "TotalRandSubset": ""}

with open(outp, "w") as f:
    json.dump(data, f)
