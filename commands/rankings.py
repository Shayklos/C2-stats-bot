import discord
from discord import app_commands
from discord.ext import commands
from discord.ui.item import Item
from typing import Any
import sys
sys.path.append('../c2-stats-bot')
from logger import *
import database, methods
from CultrisView import CultrisView

class RankingsView(CultrisView):

    def __init__(self, bot, author, page):
        super().__init__(bot=bot, author=author)
        self.command = '/rankings'
        
        self.interactionUser = author
        self.page = page


    async def createEmbed(self, page):
        pageSize = 20 
        start = pageSize * (page - 1) + 1
        end = start + pageSize -1
        data = await database.getRankings(self.bot.db, start, end)
        description = ""
        for element in data:
            description += f"{start}. [{element[1]}](https://gewaltig.net/ProfileView/{element[0]}) {element[2]}\n"
            start+=1

        embed = discord.Embed(
                color=0x0B3C52,
                description=description,
                title=f"Leaderboard"
            )
        return embed


    @discord.ui.button(label="Page down", row = 0, style=discord.ButtonStyle.primary, emoji="⏬") 
    async def page_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.page = max(1, self.page-1)
        embed = await self.createEmbed(self.page)
        await interaction.response.edit_message(embed=embed, view = self)



    @discord.ui.button(label="Page up", row = 0, style=discord.ButtonStyle.primary, emoji="⏫") 
    async def page_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.page +=1
        embed = await self.createEmbed(self.page)
        await interaction.response.edit_message(embed=embed, view = self)



class Rankings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 

    @app_commands.command(description="Displays an approximation of the current leaderboard. It may not be accurate.")
    @app_commands.describe(page = "The page you want to see (by default 1). Negative page numbers are not allowed here.")
    async def rankings(self, interaction: discord.Interaction, page: app_commands.Range[int, 1] = 1):
        correct = await methods.checks(interaction)
        if not correct:
            return
        
        view = RankingsView(self.bot, interaction.user, page)

        embed = await view.createEmbed(page)
        await interaction.response.send_message(embed = embed, view = view)
        view.message = await interaction.original_response()



async def setup(bot: commands.Bot):
    await bot.add_cog(Rankings(bot))
    print(f"Loaded /rankings command.")