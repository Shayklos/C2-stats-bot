import discord
from discord import app_commands
from discord.ext import commands
from discord.ui.item import Item
from typing import Any
import sys
from os import sep
sys.path.append(f'..{sep}c2-stats-bot')
from logger import *
import database, methods
from CultrisView import CultrisView
from settings import COLOR_Default

class RankView(CultrisView):
    def __init__(self, bot, author, page):
        super().__init__(bot=bot, author=author)
        self.command = '/rank'


class Rank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 

    @app_commands.command(description="Finds an user in common leaderboards.")
    async def rank(self, interaction: discord.Interaction, username: str = None):
        correct = await methods.checks(interaction)
        if not correct: return


async def setup(bot: commands.Bot):
    await bot.add_cog(Rank(bot))
    print(f"Loaded /rank command.")