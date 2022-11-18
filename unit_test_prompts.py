import json
import os
import pathlib
import sys

import prompts
from distill4_normalize import Distill4Inst, ctx

# avrae imports
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "avrae"))
from avrae.cogs5e.initiative import Combat
from avrae.cogs5e.models.character import Character


class UnitTestScenario(Distill4Inst):
    def __init__(self, scenario_dir: pathlib.Path):
        super().__init__([])
        self.scenario_dir = scenario_dir

        with open(scenario_dir / "combat.json") as f:
            self.combat_dict = json.load(f)

        with open(scenario_dir / "characters.json") as f:
            characters_list = json.load(f)
            for character in characters_list:
                owner = character["owner"]
                upstream = character["upstream"]
                self.characters[(owner, upstream)] = Character.from_dict(character)

        with open(scenario_dir / "utterance.txt") as f:
            self.utterance = f.read().strip()

        with open(scenario_dir / "command.txt") as f:
            self.gold_command = f.read().strip()

    def create_prompt(self):
        combat_before = Combat.from_dict_sync(self.combat_dict, ctx)
        actor_list_before = [
            self.normalize_actor(actor, combat_before) for actor in combat_before.get_combatants(groups=False)
        ]

        current = combat_before.current_combatant
        current_actor = self.normalize_actor(current, combat_before) if current is not None else None

        prompt_data = {
            "before_utterances": [self.utterance],
            "combat_state_before": actor_list_before,
            "current_actor": current_actor,
        }

        prompt = prompts.utt_cmd_prompt(prompt_data)
        with open(self.scenario_dir / "prompt.txt", "w") as f:
            f.write(prompt)

        abl_prompt = prompts.utt_cmd_prompt(prompt_data, ablations=["actors", "current"])
        with open(self.scenario_dir / "abl_prompt.txt", "w") as f:
            f.write(abl_prompt)


def main():
    unit_test_dir = pathlib.Path("unit_tests")
    for dirpath in unit_test_dir.iterdir():
        if not dirpath.is_dir():
            continue
        print(dirpath)
        scenario = UnitTestScenario(dirpath)
        scenario.create_prompt()


if __name__ == "__main__":
    main()
# "before_utterances": utterance.txt,
# "combat_state_before": actor_list_before,  # list of actors
# "current_actor": current_actor,  # actor, nullable
