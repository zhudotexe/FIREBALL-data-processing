"""
Depends on results/merge_results.py
"""
import pathlib
import re
import sys

import tqdm
from profanityfilter import ProfanityFilter

from discord_render import MessageRenderer

sys.path.append("..")

import prompts
from dataset.utils import combat_dir_iterator, read_jsonl_file
from distill4_normalize import Distill4Inst
from heuristics.utils import AVRAE_ID

DATA_DIR = pathlib.Path("../data/")

HUMAN_EVAL_QUALTRICS = pathlib.Path("human-eval-qualtrics.txt")
HUMAN_EVAL_DATA = pathlib.Path("human-eval-sta-nar.jsonl")

TASK_INSTRUCTIONS = """
<p><strong>Instructions</strong><br>
In this task, you will see part of a play-by-post D&D combat using Avrae in the form of Discord messages leading up to
an Avrae action. The caster's description and current initiative list are listed along with the
Discord messages. The messages that are shown as context are real messages from players. Your job is to read the context
and then rate different responses for the dungeon master's narration of the action. Please note that the context you are
given represents only a part of the players’ past conversations/interactions with one another during the game.</p><br>
""".strip()

SENSE_INSTRUCTIONS = """
<strong>Does the response make sense? (1 is best)</strong><br>
<span style="font-size:16px;">Rank each response by whether or not you think it makes sense. Use your common sense here.
Is the response completely reasonable in terms of the rules of D&amp;D?<br>
The response "makes sense" if it is cohesive as a standalone statement, consistent with the rules of the game, and the
elements/entities mentioned are plausible, given the prior context.<br>
If anything seems off—not fluent, confusing, illogical, out of context, or wrong according to the rules of D&amp;D
—then rank it lower. If in doubt about a response, rank it lower.</span>
""".strip()

SPECIFIC_INSTRUCTIONS = """
<strong>Is the response specific? (1 is best)</strong><br>
<span style="font-size:16px;">Rank each response by how specific it is to the given context. In other words, how well 
do you think that the response represents the action the character actually took and its results?<br>
The response is "specific" if it flows logically from the narrative established by the prior context.<br>
Note: It is possible for a response to "make sense" (due to being cohesive, consistent and plausible in and of itself),
but be ranked less "specific" when it is not a logical next step in the overall game progression.<br>
Note: "Specific" for the purposes of this task does not have to do with how detailed the response is per se; a response
can be fairly general in its language, but still qualify as "specific" when it is a logical next step in the overall
game progression.</span>
""".strip()

INTERESTING_INSTRUCTIONS = """
<strong>How interesting is the response? (1 is best)</strong><br>
<span style="font-size:16px;">Rank a response as more "Interesting" if the response would likely catch someone's
attention or arouse curiosity in the game; or it is insightful, creative, or witty with respect to the game. If the
response is monotonous and predictable, or if you’re unsure, then rank it lower.</span>
""".strip()


class HumanEvalInst(Distill4Inst):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.author_id_map = {}

    def normalize_messages(self):
        """Removes mentions, tupper, emoji, etc; anonymize author names"""
        for idx, msg in enumerate(self.events.copy()):
            if msg["event_type"] != "message":
                continue
            content = msg["content"]
            # remove any Tupper markers
            similar_message = self.find(
                lambda e: e["event_type"] == "message"
                and e["author_id"] != msg["author_id"]
                and e["content"] in content
                and e["content"]
                and e.get("author_bot", True),
                after=idx,
                before=idx + 16,
            )
            if similar_message is not None:
                similar_content = similar_message["content"]
                # the new content must be at least 80% of the old
                len_ratio = len(similar_content) / len(content)
                if 0.7 < len_ratio < 1:
                    self.events.remove(similar_message)

            # remove user, role, channel mentions
            msg["content"] = re.sub(r"<(@[!&]?|#)\d{17,20}>", "", content)

            # replace custom emoji with just their name
            msg["content"] = re.sub(r"<a?(:\w+?:)\d{17,20}>", r"\1", content)

            # anonymize author nick, unless it's Avrae
            author_id = msg["author_id"]
            if author_id == AVRAE_ID:
                author_name = "Avrae"
            elif author_id in self.author_id_map:
                author_name = f"Player {self.author_id_map[author_id]}"
            else:
                self.author_id_map[author_id] = len(self.author_id_map)
                author_name = f"Player {self.author_id_map[author_id]}"
            msg["author_name"] = author_name


def prep_human_eval():
    data = list(read_jsonl_file(HUMAN_EVAL_DATA))

    keys = (
        "gold",
        "prediction_full",
        "prediction_nostate",
        "prediction_command_utterance",
        "prediction_dialog_continuation",
    )
    data = data[:75]  # 75 instances for human eval
    qualtrics_out = ["[[AdvancedFormat]]"]
    for idx, d in tqdm.tqdm(enumerate(data)):
        qualtrics_out.append(f"[[Block:Block{idx}]]")
        # ---- ScenarioN ----
        qualtrics_out.append("[[Question:DB]]")
        qualtrics_out.append(f"[[ID:Scenario{idx}]]")
        # the human gets:
        # last 15 messages before the last command idx, which should include the avrae embeds
        # the combat state after the command
        # the caster desc
        event_stream = combat_dir_iterator(DATA_DIR / d["instance_id"])
        inst = HumanEvalInst(event_stream)
        inst.normalize_messages()

        # messages
        message_history = list(inst.find_all(lambda e: e["event_type"] == "message", before=d["command_idxs"][-1]))
        last_15_messages = message_history[-15:]
        renderer = MessageRenderer(last_15_messages)

        # combat state
        state_str = "\n".join([f"- {prompts.stringify_actor(a)['short']}" for a in d["combat_state_after"]])

        # caster desc
        caster_strs = prompts.stringify_actor(d["caster_after"])
        caster_desc = MessageRenderer.render_markdown(caster_strs["description"]) + caster_strs["long"]

        qualtrics_out.append(TASK_INSTRUCTIONS)

        qualtrics_out.append("<strong>Caster's Description</strong><br>")
        qualtrics_out.append(f"<pre>{caster_desc}</pre><br>")

        qualtrics_out.append("<strong>Context</strong><br>")
        qualtrics_out.append(renderer.render_messages())

        qualtrics_out.append("<strong>Initiative List</strong><br>")
        qualtrics_out.append(f"<pre>{state_str}</pre><br>")

        # then, all the choices to rank
        # ---- SenseN ----
        qualtrics_out.append("[[Question:RO]]")
        qualtrics_out.append(f"[[ID:Sense{idx}]]")
        qualtrics_out.append(SENSE_INSTRUCTIONS)
        qualtrics_out.append("[[AdvancedChoices]]")
        for choice_idx, choice_key in enumerate(keys):
            qualtrics_out.append(f"[[Choice:{choice_idx + 1}]]")
            qualtrics_out.append(MessageRenderer.render_markdown(d[choice_key]))
        # ---- SpecificN ----
        qualtrics_out.append("[[Question:RO]]")
        qualtrics_out.append(f"[[ID:Specific{idx}]]")
        qualtrics_out.append(SPECIFIC_INSTRUCTIONS)
        qualtrics_out.append("[[AdvancedChoices]]")
        for choice_idx, choice_key in enumerate(keys):
            qualtrics_out.append(f"[[Choice:{choice_idx + 1}]]")
            qualtrics_out.append(MessageRenderer.render_markdown(d[choice_key]))
        # ---- InterestingN ----
        qualtrics_out.append("[[Question:RO]]")
        qualtrics_out.append(f"[[ID:Interesting{idx}]]")
        qualtrics_out.append(INTERESTING_INSTRUCTIONS)
        qualtrics_out.append("[[AdvancedChoices]]")
        for choice_idx, choice_key in enumerate(keys):
            qualtrics_out.append(f"[[Choice:{choice_idx + 1}]]")
            qualtrics_out.append(MessageRenderer.render_markdown(d[choice_key]))
        # ---- TimerN ----
        qualtrics_out.append("[[Question:Timing]]")
        qualtrics_out.append(f"[[ID:Timer{idx}]]")
        qualtrics_out.append("")

    # save human eval qualtrics
    out = "\n".join(qualtrics_out)
    pf = ProfanityFilter()
    pf.set_censor("-")
    with open("profanity.txt") as f:
        pf.define_words([line.strip() for line in f.readlines()])
    out = pf.censor(out)
    HUMAN_EVAL_QUALTRICS.write_text(out)


if __name__ == "__main__":
    prep_human_eval()
