
from avrae.tests.utils import active_combat


async def test_assertion(avrae, dhttp):
    # TODO: load the characters and relevant combat state from characters.json and combat.json

    prompt = None  # TODO: load from prompt.txt

    def predict(p):
        return None  # TODO: call GPT-3 (or baseline model)

    combat = await active_combat(avrae)
    avrae.message(predict(prompt), author_id=combat.current_combatant.controller_id)
    await dhttp.drain()

    # assertions here
    effects = (await active_combat(avrae)).get_combatant("Noxxis Blazehammer").get_effects()
    assert len(effects) == 1
    assert effects[0].name == "Feeling Inspired"
