import asyncio
import csv
import os

import disnake
from disnake.ext import commands
from disnake.ext.commands import Bot

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = 187421759484592128
EVAL_GUILD_ID = 1048425749763334154

with open("eval_users.txt") as f:
    user_ids = [int(line.strip()) for line in f.readlines()]

bot = Bot(command_prefix=commands.when_mentioned, intents=disnake.Intents.all())


@bot.event
async def on_ready():
    print("ready")


@bot.slash_command()
async def validate_users(inter: disnake.ApplicationCommandInteraction):
    if inter.author.id != ADMIN_USER_ID:
        return
    valid = []
    invalid = []
    for user_id in user_ids:
        user = bot.get_user(user_id)
        if user is not None:
            valid.append(user_id)
        else:
            invalid.append(user_id)
    await inter.send(f"{len(valid)} valid, {len(invalid)} invalid")
    await inter.send(f"invalid:\n" + "\n".join(map(str, invalid)))


@bot.slash_command()
async def send_msg(inter: disnake.ApplicationCommandInteraction, message: str):
    if inter.author.id != ADMIN_USER_ID:
        return
    await inter.response.defer()
    valid = []
    invalid = []
    for user_id in user_ids:
        user = bot.get_user(user_id)
        if user is None:
            continue
        try:
            await user.send(message)
        except disnake.DiscordException as e:
            print(f"{user_id} FAIL")
            print(e)
            invalid.append(user_id)
        else:
            print(f"{user_id} OK")
            valid.append(user_id)
        await asyncio.sleep(5)
    print(f"invalid:\n" + "\n".join(map(str, invalid)))
    await inter.send(f"{len(valid)} ok, {len(invalid)} not ok\ninvalid:\n" + "\n".join(map(str, invalid)))


@bot.slash_command()
async def in_server(inter: disnake.ApplicationCommandInteraction):
    if inter.author.id != ADMIN_USER_ID:
        return
    guild = bot.get_guild(EVAL_GUILD_ID)
    print(f"guild members:\n" + "\n".join(str(m.id) for m in guild.members))
    await inter.send("ok")


@bot.slash_command()
async def send_keys(inter: disnake.ApplicationCommandInteraction):
    if inter.author.id != ADMIN_USER_ID:
        return
    await inter.response.defer()

    dice_keys = {}  # user id (int) -> key
    book_keys = {}
    with open("dice_keys.tsv") as f:
        reader = csv.reader(f, delimiter="\t", quotechar='"')
        for key, _, _, _, _, _, _, user_id in reader:
            dice_keys[int(user_id)] = key
    with open("motm_keys.tsv") as f:
        reader = csv.reader(f, delimiter="\t", quotechar='"')
        for key, _, _, _, _, _, _, user_id in reader:
            book_keys[int(user_id)] = key

    print(dice_keys)
    print(book_keys)

    valid = []
    invalid = []
    for user_id in dice_keys:
        user = bot.get_user(user_id)
        if user is None:
            print(f"{user_id} FAIL: not found")
            continue
        try:
            message = (
                f"Thanks for participating in the evaluation! Here are your codes:\n"
                f"**Researcher's Dice (Digital Dice)**: `{dice_keys[user_id]}`\n"
            )
            if user_id in book_keys:
                message += (
                    f"**Mordenkainen Presents: Monsters of the Multiverse (Digital Sourcebook)**: "
                    f"`{book_keys[user_id]}`\n"
                )
            message += "You can redeem your code at <https://www.dndbeyond.com/marketplace/redeem-key>!"
            await user.send(message)
        except disnake.DiscordException as e:
            print(f"{user_id} FAIL")
            print(e)
            invalid.append(user_id)
        else:
            print(f"{user_id} OK")
            valid.append(user_id)
        await asyncio.sleep(5)
    print(f"invalid:\n" + "\n".join(map(str, invalid)))
    print(f"valid:\n" + "\n".join(map(str, valid)))
    await inter.send(f"{len(valid)} ok, {len(invalid)} not ok")


if __name__ == "__main__":
    bot.run(TOKEN)
