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
STAT_TO_COLUMN = {
    'Played rounds': 'playedRounds',
    'Wins': 'wins',
    'Max BPM': 'maxBPM',
    'Average BPM': 'avgBPM',
    'Lines received': 'linesGot',
    'Lines sent': 'linesSent',
    'Lines blocked': 'linesBlocked',
    'Placed blocks': 'blocksPlaced',
    'Number of 10s': '"10s"',
    'Number of 11s': '"11s"',
    'Number of 12s': '"12s"',
    'Number of 13s': '"13s"',
    'Number of 14s': '"14s"',
    'Sum of max combos': 'comboSum',
    'Recorded peak score': 'peakRankScore',
    'Played time': 'playedMin',
    'Played time (Standard)': 'standardTime',
    'Played time (Cheese)': 'cheeseTime',
    'Played time (Teams)': 'teamsTime'
    }

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

async def getLeaderboard(db: aiosqlite.Connection, column, page, decimals = 0, time = False):
    if page > 0:
        leaderboard = await db.execute(f"""select userId, name, {column} from Users
                                        where playedRounds > 300 and {column}
                                       order by {column} desc
                            limit {database.embedPageSize} offset {database.embedPageSize * (page - 1)}""")
    else:
        leaderboard = await db.execute(f"""select userId, name, {column} from Users 
                                       where playedRounds > 300
                                       order by {column} asc
                            limit {database.embedPageSize} offset {database.embedPageSize * (-page - 1)}""")
    
    description = ""
    place = database.embedPageSize * (page - 1) + 1 if page > 0 else database.embedPageSize * (-page - 1) + 1
    async for row in leaderboard:
        description += line(place, row['userId'], row['name'], row[column.strip('"')], decimals, time)
        place = place + 1

    return description

async def getPageOfUserInLeaderboard(db: aiosqlite.Connection, column, name):
    # In reality this does the same query twice but I cannot be bothered
    res = await db.execute(f"""
        with tab as (select row_number() over (order by {column} desc) as i, userId, name, {column} from Users
            where playedRounds > 300 and {column}
            order by {column} desc)
            
        select ceil(i / {database.embedPageSize}.0) from tab where name = "{name}"
            """)
    result = await res.fetchone()
    if result:
        return int(result[0])
    else:
        return None

class FindUserModal(discord.ui.Modal):
    def __init__(self, view, *, title: str = "User finder", timeout: float | None = None) -> None:
        super().__init__(title=title, timeout=timeout)
        self.view: AllTimeBestView = view

    name = discord.ui.TextInput(
        label='Username',
        placeholder='Write the username to find here',
    )
    async def on_submit(self, interaction: discord.Interaction):
        embed, msg = await self.view.findUser(self.name.value)
        if not embed:
            await interaction.response.edit_message(
            content=f"No user named {msg}",
            view=self.view
            )
            return 
        
        await interaction.response.edit_message(
            content=msg,
            embed=embed,
            view=self.view
            )

class AllTimeBestView(CultrisView):

    def __init__(self, bot, author, stat, page):
        super().__init__(bot=bot, author=author)
        self.command = '/leaderboard'
        
        self.interactionUser = author
        self._stat = stat
        self.page = page
        self.absolute = False

    async def getData(self, page, stat):
        kwargs = {'page': page}
        if stat not in STAT_TO_COLUMN.keys():
            return None, "Did you choose a stat?"
        self.column = STAT_TO_COLUMN[stat]
        
        match stat:
            case 'Max BPM' | 'Average BPM' | 'Recorded peak score':
                kwargs['decimals'] = 2
            case 'Played time' | 'Played time (Standard)' | 'Played time (Cheese)' | 'Played time (Teams)':
               kwargs['time'] = True

        
        description = await getLeaderboard(self.bot.db, self.column, **kwargs)
        
        title = stat + " leaderboard (all-time)"
        return description, title

    async def findUser(self, name: str):
        ratio, userId, username = await database.fuzzysearch(self.bot.db, name.lower())
        msg = None if ratio == 100 else f"No user found with name \'{name}\'. Did you mean \'{username}\'?"
        self.page = await getPageOfUserInLeaderboard(self.bot.db, self.column, username)
        if not self.page:
            return None, username
        description, title = await self.getData(self.page, self._stat)
        embed = discord.Embed(
                color=COLOR_Default,
                description=description,
                title=title)
        embed.set_footer(text = f"Page {self.page}")

        return embed, msg

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
      
    @discord.ui.button(label="Find user", row = 2, style=discord.ButtonStyle.primary, emoji="🔍") 
    async def find_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        await interaction.response.send_modal(FindUserModal(self))


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

        stats = sorted(STAT_TO_COLUMN.keys())
        return [
            app_commands.Choice(name=stat, value=stat)
            for stat in stats if current.lower() in stat.lower()
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(AllTimeBest(bot))
    print(f"Loaded /alltime-best command.")
