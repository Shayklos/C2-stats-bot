import discord
from discord import app_commands
from discord.ext import commands
import sys
from os import sep
sys.path.append(f'..{sep}c2-stats-bot')
import database, methods
from settings import COLOR_Default

class WeeklyBest(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 

    @app_commands.command(description="Top 5 in SPM and Cheese times in the last 7 days.")
    async def weeklybest(self, interaction: discord.Interaction):
        correct = await methods.checks(interaction)
        if not correct:
            return
        top5SPM, top5Cheese = await database.weekly_best(self.bot.db)
        embed = discord.Embed(
                title="Weekly Best",
                color=COLOR_Default,
            )
        embed.add_field(name = "Top 5 SPM (7d)", value = 
                        f"""**{top5SPM[0][0]}** - {round(top5SPM[0][1])}
    **{top5SPM[1][0]}** - {round(top5SPM[1][1])}
    **{top5SPM[2][0]}** - {round(top5SPM[2][1])}
    **{top5SPM[3][0]}** - {round(top5SPM[3][1])}
    **{top5SPM[4][0]}** - {round(top5SPM[4][1])}

    """, inline=True)
        embed.add_field(name = '\u2800', value = "\u2800\n\u2800\n\u2800\n\u2800\n\u2800")

        embed.add_field(name = "Top 5 Cheese times (7d)", value = 
                        f"""**{top5Cheese[0][0]}** - {round(top5Cheese[0][1],2)}
    **{top5Cheese[1][0]}** - {round(top5Cheese[1][1],2)}
    **{top5Cheese[2][0]}** - {round(top5Cheese[2][1],2)}
    **{top5Cheese[3][0]}** - {round(top5Cheese[3][1],2)}
    **{top5Cheese[4][0]}** - {round(top5Cheese[4][1],2)}

    """, inline=True)
        await interaction.response.send_message(embed=embed)



async def setup(bot: commands.Bot):
    await bot.add_cog(WeeklyBest(bot))
    print(f"Loaded /weeklybest command.")