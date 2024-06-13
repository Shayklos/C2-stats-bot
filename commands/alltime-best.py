import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands
import sys
from os import sep

sys.path.append(f"..{sep}c2-stats-bot")
from CultrisView import CultrisView
import database, methods
from settings import COLOR_Default

"""Similar to /leaderboard command, but tried to refactor the code so its more clean. 
So it may no use functions designed specifically for this sort of stuff"""

def url(id):
    return f"https://gewaltig.net/ProfileView/{id}"

def line(n, id, name, stat, decimals, time):
    if decimals:
        value = round(stat, decimals)
    elif time:
        value = f"{int(stat//60)}h {round(stat%60, 1)}m"
    else:
        value = f'{stat:,}' # Thousands separator

    return f"{n}. [{name}]({url(id)}) {value}\n"

async def getLeaderboard(db: aiosqlite.Connection, column, page, order = 'desc', decimals = 0, time = False):
    if page > 0:
        leaderboard = await db.execute(f"""select userId, name, {column} from Users
                                        where playedRounds > 300 and {column}
                                       order by {column} {order}
                            limit {database.embedPageSize} offset {database.embedPageSize * (page - 1)}""")
    else:
        order = 'asc' if order == 'desc' else 'asc'
        leaderboard = await db.execute(f"""select userId, name, {column} from Users 
                                       where playedRounds > 300
                                       order by {column} {order}
                            limit {database.embedPageSize} offset {database.embedPageSize * (-page - 1)}""")
    
    description = ""
    place = database.embedPageSize * (page - 1) + 1 if page > 0 else database.embedPageSize * (-page - 1) + 1
    async for row in leaderboard:
        description += line(place, row['userId'], row['name'], row[column.strip('"')], decimals, time)
        place = place + 1

    return description


class AllTimeBestView(CultrisView):

    def __init__(self, bot, author, stat, page):
        super().__init__(bot=bot, author=author)
        self.command = '/leaderboard'
        
        self.interactionUser = author
        self._stat = stat
        self.page = page
        self.absolute = False

    async def getData(self, page, stat):
        match stat:
            case 'Played rounds':
                description = await getLeaderboard(self.bot.db, 'playedRounds', page = page)
            case 'Wins':
                description = await getLeaderboard(self.bot.db, 'wins', page = page)
            case 'Max BPM':
                description = await getLeaderboard(self.bot.db, 'maxBPM', page = page, decimals = 2)
            case 'Average BPM':
                description = await getLeaderboard(self.bot.db, 'avgBPM', page = page, decimals = 2)
            case 'Lines received':
                description = await getLeaderboard(self.bot.db, 'linesGot', page = page)
            case 'Lines sent':
                description = await getLeaderboard(self.bot.db, 'linesSent', page = page)
            case 'Lines blocked':
                description = await getLeaderboard(self.bot.db, 'linesBlocked', page = page)
            case 'Placed blocks':
                description = await getLeaderboard(self.bot.db, 'blocksPlaced', page = page)
            case 'Number of 10s':
                description = await getLeaderboard(self.bot.db, '"10s"', page = page)
            case 'Number of 11s':
                description = await getLeaderboard(self.bot.db, '"11s"', page = page)
            case 'Number of 12s':
                description = await getLeaderboard(self.bot.db, '"12s"', page = page)
            case 'Number of 13s':
                description = await getLeaderboard(self.bot.db, '"13s"', page = page)
            case 'Number of 14s':
                description = await getLeaderboard(self.bot.db, '"14s"', page = page)
            case 'Sum of max combos':
                description = await getLeaderboard(self.bot.db, 'comboSum', page = page)
            case 'Recorded peak score':
                description = await getLeaderboard(self.bot.db, 'peakRankScore', page = page, decimals=2)
            case 'Played time':
                description = await getLeaderboard(self.bot.db, 'playedMin', page = page, time = True)
            case 'Played time (Standard)':
                description = await getLeaderboard(self.bot.db, 'standardTime', page = page, time = True)
            case 'Played time (Cheese)':
                description = await getLeaderboard(self.bot.db, 'cheeseTime', page = page, time = True)
            case 'Played time (Teams)':
                description = await getLeaderboard(self.bot.db, 'teamsTime', page = page, time = True)
        
        title = stat + " leaderboard (all-time)"
        return description, title

    # @discord.ui.button(label="Sort by count", row = 2, style=discord.ButtonStyle.primary) 
    # async def absolute_relative(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     self.absolute = not self.absolute
    #     button.label = 'Sort by ratio' if button.label == 'Sort by count' else 'Sort by count'
    #     description, title = await self.getData(self.page, self._stat, self.days, absolute=self.absolute)
    #     await interaction.response.edit_message(
    #         embed=discord.Embed(
    #                 color=COLOR_Default,
    #                 description=description,
    #                 title=title),
    #         view=self
    #         )

    @discord.ui.button(label="Page down", row = 1, style=discord.ButtonStyle.primary, emoji="⬅️") 
    async def page_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page = -1 if self.page == 1 else self.page - 1
        description, title = await self.getData(self.page, self._stat)
        embed = discord.Embed(
                    color=COLOR_Default,
                    description=description,
                    title=title)
        embed.set_footer(text = f"Page {self.page}")

        await interaction.response.edit_message(
            embed=embed,
            view=self
            )

    @discord.ui.button(label="Page up", row = 1, style=discord.ButtonStyle.primary, emoji="➡️") 
    async def page_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page = 1 if self.page == -1 else self.page + 1
        description, title = await self.getData(self.page, self._stat)
        embed = discord.Embed(
                    color=COLOR_Default,
                    description=description,
                    title=title)
        embed.set_footer(text = f"Page {self.page}")
        
        await interaction.response.edit_message(
            embed=embed,
            view=self
            )
      
class AllTimeBest(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(
        description="All time best leaderboards. These don't change too often!",
        name='alltime-best'
    )
    async def alltimebest(
        self,
        interaction: discord.Interaction,
        stat: str,
        page: int = 1
    ):
        correct = await methods.checks(interaction)
        if not correct:
            return

        view = AllTimeBestView(self.bot, interaction.user, stat, page)

        #Contents of message
        await interaction.response.defer()
        description, title = await view.getData(page, stat)
        if not description:
            await interaction.followup.send(title, ephemeral=True)
            return
        
        embed = discord.Embed(
                color=COLOR_Default,
                description=description,
                title=title)
        embed.set_footer(text = f"Page {page}")

        await interaction.followup.send(embed=embed, view=view)
        view.message = await interaction.original_response()



    @alltimebest.autocomplete('stat')
    async def alltimebest_autocomplete(self, interaction: discord.Interaction, current: str):

        stats = sorted([
            'Played rounds',
            'Wins',
            'Max BPM',
            'Average BPM',
            'Lines received',
            'Lines sent',
            'Lines blocked',
            'Placed blocks',
            'Number of 10s',
            'Number of 11s',
            'Number of 12s',
            'Number of 13s',
            'Number of 14s',
            'Sum of max combos',
            'Recorded peak score',
            'Played time',
            'Played time (Standard)',
            'Played time (Cheese)',
            'Played time (Teams)',
        ])
        return [
            app_commands.Choice(name=stat, value=stat)
            for stat in stats if current.lower() in stat.lower()
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(AllTimeBest(bot))
    print(f"Loaded /alltime-best command.")
