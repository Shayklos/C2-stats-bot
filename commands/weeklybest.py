import discord
from discord import app_commands
from discord.ext import commands
import sys
from os import sep

sys.path.append(f"..{sep}c2-stats-bot")
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
    string = ""
    for row in top:
        plus = (
            "+" if row[2] == 1 and row[3] != 1 else ""
        )  # Add a + if user won the round and he wasn't alone in the room
        string += f"**{row[0]}** - {int(row[1]//60)}:{round(row[1]%60, 1)} {plus}\n"
    return string[:-1]


class WeeklyBest(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(
        description="Tops in SPM, Cheese times and Survivor times!"
    )
    async def weeklybest(
        self,
        interaction: discord.Interaction,
        top: app_commands.Range[int, 1] = 5,
        days: app_commands.Range[int, 0, database.dbDaysLimit] = 7,
    ):
        correct = await methods.checks(interaction)
        if not correct:
            return
        top5SPM, top5Cheese, top5Survivor = await database.weekly_best(self.bot.db, days, top)
        spm, cheese, survivor = (
            topSPM_str(top5SPM),
            topCheese_str(top5Cheese),
            topSurvivor_str(top5Survivor),
        )

        if len(spm) > 1024 or len(cheese) > 1024 or len(survivor) > 1024:
            await interaction.response.send_message(
                "Too big of a top! I can only write 1024 characters in a field... that runs out quickly.",
                ephemeral=True,
            )
            return

        if days == 7:
            title = "Weekly Best"
        else:
            title = f"{days} days Best"

        embed = discord.Embed(
            title=title,
            color=COLOR_Default,
        )
        embed.add_field(name=f"Top {top} SPM ({days}d)", value=spm, inline=True)

        embed.add_field(
            name=f"Top {top} Cheese times ({days}d)", value=cheese, inline=True
        )

        embed.add_field(
            name=f"Top {top} Survivor times ({days}d)", value=survivor, inline=True
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklyBest(bot))
    print(f"Loaded /weeklybest command.")
