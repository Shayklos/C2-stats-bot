import discord
from discord import app_commands
from discord.ext import commands
import sys
sys.path.append('../c2-stats-bot')
import database, methods


class LegacyStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 


    @app_commands.command(description="Returns all-time stats of a user. If you can't find the user, maybe try with an old nickname?")
    @app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
    async def legacystats(self, interaction: discord.Interaction, username: str=None):
        correct = await methods.checks(interaction)
        if not correct:
            return
        
        if not username:
            username = interaction.user.display_name
        ratio, userId, user = database.fuzzysearch(self.bot.db, username) #ej (80, 5840, Shay)

        msg = None
        if ratio != 100:
            msg = f"No user found with name \'{username}\'. Did you mean \'{user}\'?"
            
        
        
        player = database.player_stats(self.bot.db, userId)
        # print(player)
        # print(timeStats)
        embed = discord.Embed(
                title=player["name"],
                color=0x0B3C52,
                url=f"https://gewaltig.net/ProfileView/{player['userId']}",
            )
        if player["rank"]:
            embed.add_field(name="Rank", value=player["rank"], inline=True)
            embed.add_field(name="Score", value=f"{player['score']:.1f}", inline=True)
            embed.add_field(name="Recorded Peak", value=f"{player['peakRank']} ({player['peakRankScore']:.1f})", inline=True)

        if player["playedRounds"]:
            embed.add_field(name="Best Combo", value=player["maxCombo"], inline=True)
            embed.add_field(name="Wins", value=methods.thousandsSeparator(player["wins"]), inline=True)
            embed.add_field(name="Games", value=f"{methods.thousandsSeparator(player['playedRounds'])} ({methods.thousandsSeparator(player['playedRoundsStandard'])} in Standard)", inline=True)

            embed.add_field(name="Max BPM", value=round(player["maxBPM"], 1), inline=True)
            embed.add_field(name="Avg BPM", value=round(player["avgBPM"], 1), inline=True)
            embed.add_field(name="Total Hours", value=f"{player['playedMin']/60:.1f}h", inline=True)

            embed.add_field(name="Standard time", value=f"{player['standardTime']/3600:.1f}h", inline=True)
            embed.add_field(name="Cheese time", value=f"{player['cheeseTime']/3600:.1f}h", inline=True)
            embed.add_field(name="Teams time", value=f"{player['teamsTime']/3600:.1f}h", inline=True)

            embed.add_field(name="Received lines", value=methods.thousandsSeparator(player["linesGot"]), inline=True)
            embed.add_field(name="Sent lines", value=methods.thousandsSeparator(player["linesSent"]), inline=True)
            embed.add_field(name="Blocked lines", value=methods.thousandsSeparator(player["linesBlocked"]), inline=True)

            embed.add_field(name="Sum of Max Combos", value=methods.thousandsSeparator(player["comboSum"]), inline=True)
            if player["maxCombo"] == 14:
                embed.add_field(name="14s", value=player["14s"], inline=True)
                embed.add_field(name="13s", value=player["13s"], inline=True)
            elif player["maxCombo"] == 13:
                embed.add_field(name="13s", value=player["13s"], inline=True)
                embed.add_field(name="12s", value=player["12s"], inline=True)
            elif player["maxCombo"] == 12:
                embed.add_field(name="12s", value=player["12s"], inline=True)
                embed.add_field(name="11s", value=player["11s"], inline=True)
            else:
                embed.add_field(name="11s", value=player["11s"], inline=True)
                embed.add_field(name="10s", value=player["10s"], inline=True)
            


        else:
            embed.add_field(name="Games", value=0, inline=True)
            
        
        embed.set_thumbnail(url=f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png")
        await interaction.response.send_message(msg, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LegacyStats(bot))