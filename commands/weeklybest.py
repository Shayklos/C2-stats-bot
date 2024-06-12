import discord
from discord import app_commands
from discord.ext import commands
import sys
from os import sep
sys.path.append(f'..{sep}c2-stats-bot')
import database, methods
from settings import COLOR_Default

def topSPM_str(top) -> str:
    string = ""
    for row in top:
        string += f"**{row[0]}** - {round(row[1])}\n"
    return string[:-1]

def topCheese_str(top) -> str:
    string = ""
    for row in top:
        string += f"**{row[0]}** - {round(row[1], 2)}\n"
    return string[:-1]

def topSurvivor_str(top) -> str:
    print(top)
    string = ""
    for row in top:
        plus = '+' if row[2] == 1 and row[3] != 1 else '' # Add a + if user won the round and he wasn't alone in the room
        string += f"**{row[0]}** - {int(row[1]//60)}:{round(row[1]%60, 1)} {plus}\n"
    return string[:-1]


class WeeklyBest(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 

    @app_commands.command(description="Top 5 in SPM and Cheese times in the last 7 days.")
    async def weeklybest(self, interaction: discord.Interaction):
        correct = await methods.checks(interaction)
        if not correct:
            return
        top5SPM, top5Cheese, top5Survivor = await database.weekly_best(self.bot.db)
        embed = discord.Embed(
                title="Weekly Best",
                color=COLOR_Default,
            )
        embed.add_field(name = "Top 5 SPM (7d)", value = topSPM_str(top5SPM), inline=True)

        # embed.add_field(name = '\u2800', value = "\u2800\n\u2800\n\u2800\n\u2800\n\u2800")

        embed.add_field(name = "Top 5 Cheese times (7d)", value = topCheese_str(top5Cheese), inline=True)

        embed.add_field(name = "Top 5 Survivor times (7d)", value = topSurvivor_str(top5Survivor), inline=True)

        await interaction.response.send_message(embed=embed)



async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklyBest(bot))
    print(f"Loaded /weeklybest command.")