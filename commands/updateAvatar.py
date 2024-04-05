import aiohttp
from discord import app_commands, Interaction
from discord.ext import commands
import sys
from os import getenv, sep

sys.path.append(f"..{sep}c2-stats-bot")
from database import fuzzysearch, player_stats
from logger import log


class UpdateAvatar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.command = "/update_avatar"
        self.bot = bot

    @staticmethod
    async def upload_hash(md5_hash):
        url = "https://c2.tail.ws/upload/gravatarhash.txt"
        auth = aiohttp.BasicAuth(getenv("VPS_USERNAME"), getenv("VPS_PASSWORD"))

        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.put(url, data=md5_hash) as response:
                if not 200 <= response.status < 300:
                    log(
                        f"Failed to upload file. Status code: {response.status}",
                        "error.txt",
                    )
                    log(await response.text(), "error.txt")
                    return 0
        return 1

    @app_commands.command(
        description="Updates the profile picture of a user ingame, if that user changed it."
    )
    @app_commands.rename(usernameInput="username")
    @app_commands.describe(
        usernameInput="Ingame username of the player you're looking for. Leave empty to use your Discord display name."
    )
    async def update_avatar(self, interaction: Interaction, usernameInput: str = None):
        if not usernameInput:
            usernameInput = interaction.user.display_name

        ratio, userId, username = await fuzzysearch(self.bot.db, usernameInput.lower())
        if ratio != 100:
            await interaction.response.send_message(
                content=f"No user found with name '{usernameInput}'. Did you mean '{username}'?"
            )
            return

        stats = await player_stats(self.bot.db, userId)
        hash = stats.get("gravatarHash")

        if await UpdateAvatar.upload_hash(hash):
            await interaction.response.send_message(
                content=f"{username}'s profile picture was succesfully changed! You may need to restart the game to see the effect.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                content="Something went wrong, couldn't upload the profile picture.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(UpdateAvatar(bot))
    print("Loaded /update_avatar command.")
