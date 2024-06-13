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

class LeaderboardView(CultrisView):

    def __init__(self, bot, author, stat, days, page):
        super().__init__(bot=bot, author=author)
        self.command = '/leaderboard'
        
        self.interactionUser = author
        self._stat = stat
        self.page = page
        self.days = days
        self.absolute = False

    async def getData(self, page, stat, days, pageSize = database.embedPageSize, absolute = False):
        if 'Combo count' not in stat:
            for item in self.children:
                if item.label == 'Sort by count':
                    self.remove_item(item)
        match stat:
            case 'Blocked%':
                data = await database.getBlockedPercent(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average percentage of blocked lines ({days} days)"

            case 'Average OPB':
                data = await database.getavgOPB(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Output per block ({days} days)"

            case 'Average OPM':
                data = await database.getavgOPM(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Output per minute ({days} days)"

            case 'Average BPM':
                data = await database.getavgBPM(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Blocks per minute ({days} days)"

            case 'Average SPM':
                data = await database.getavgSPM(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Sent per minute ({days} days)"

            case 'Time played':
                data = await database.getTimePlayed(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize, isTime = True)
                title=f"Most active players ({days} days)" if page > 0 else f"Least active players ({days} days)"

            case 'Sent lines':
                data = await database.getSent(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Total lines sent ({days} days)"
                
            case 'Netscores':
                data = await database.getNetscores(self.bot.db, days=days) if 1 < days <= 7 else None
                page = 1 if data and pageSize*(page - 1) > len(data) else page
                if data:
                    description=methods.getPage(page, data, pageSize = pageSize)
                else:
                    description = "Use /stats to see 1 day Netscores." if days == 1 else "Netscores data is only supported for up to a week."

                title=f"Netscores ({days} days)"

            case 'Average best combo':
                data = await database.getCombos(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average best combo ({days} days)"

            case 'Power':
                data = await database.getPower(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Power ({days} days)"

            case 'Efficiency':
                data = await database.getPPB(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Efficiency ({days} days)"

            case other:
                if 'Combo count' in other:
                    start, end = other.find('(')+1, other.find(')')
                    if start == -1 or end == -1:
                        msg = f"""Incorrect syntax! Conditional operators allowed are
1. nothing or = or == (equal)
1. != or <> (not equal)
1. < (less than)
1. <= or ≤ (less or equal than)
1. \> (greater than)
1. >= or ≥ (greater or equal than) 
1. | or || (or)
1. & or && (and)

So something like 
«Combo count (13)» would count combos that are equal to 13,
«Combo count (<6)» would count combos that are strictly less than 6, and,
«Combo count (<=3||>10)» would count combos that are either less or equal than 3 or strictly greater than 10.
                        """
                        return None, msg
                    condition = other[start:end]
                    data, title = await database.getComboCount(self.bot.db, condition, days=days, absolute=absolute, returnTitle=True)
                    page = 1 if pageSize*(page - 1) > len(data) else page
                    description=methods.getPage(page, data, pageSize = pageSize)
                    title += f" ({days} days)"

                else:
                    return None, 'Did you choose a stat?'
        
        return description, title

    @discord.ui.button(label="Sort by count", row = 2, style=discord.ButtonStyle.primary) 
    async def absolute_relative(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.absolute = not self.absolute
        button.label = 'Sort by ratio' if button.label == 'Sort by count' else 'Sort by count'
        description, title = await self.getData(self.page, self._stat, self.days, absolute=self.absolute)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=COLOR_Default,
                    description=description,
                    title=title),
            view=self
            )

    @discord.ui.button(label="Week down", row = 0, style=discord.ButtonStyle.primary, emoji="⏬") 
    async def week_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.days = max(1, self.days-7)
        if self.days == 1:
            self.disable_buttons(["Day down", "Week down"])
        self.enable_buttons(["Day up", "Week up"])

        description, title = await self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=COLOR_Default,
                    description=description,
                    title=title),
            view=self
            )


    @discord.ui.button(label="Day down", row = 0, style=discord.ButtonStyle.primary, emoji="⬇️") 
    async def day_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.days = max(1, self.days-1)
        if self.days == 1:
            self.disable_buttons(["Day down", "Week down"])
        self.enable_buttons(["Day up", "Week up"])

        description, title = await self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=COLOR_Default,
                    description=description,
                    title=title),
            view=self
            )

    @discord.ui.button(label="Page down", row = 1, style=discord.ButtonStyle.primary, emoji="⬅️") 
    async def page_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page = -1 if self.page == 1 else self.page - 1
        description, title = await self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=COLOR_Default,
                    description=description,
                    title=title),
            view=self
            )

    @discord.ui.button(label="Page up", row = 1, style=discord.ButtonStyle.primary, emoji="➡️") 
    async def page_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page = 1 if self.page == -1 else self.page + 1
        description, title = await self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=COLOR_Default,
                    description=description,
                    title=title),
            view=self
            )

    @discord.ui.button(label="Day up", row = 0, style=discord.ButtonStyle.primary, emoji="⬆️") 
    async def day_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.days = min(database.dbDaysLimit, self.days+1)
        if self.days == database.dbDaysLimit:
            self.disable_buttons(["Day up", "Week up"])
        self.enable_buttons(["Day down", "Week down"])

        description, title = await self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=COLOR_Default,
                    description=description,
                    title=title),
            view=self
            )
  
    @discord.ui.button(label="Week up", row = 0, style=discord.ButtonStyle.primary, emoji="⏫") 
    async def week_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.days = min(database.dbDaysLimit, self.days+7)
        if self.days == database.dbDaysLimit:
            self.disable_buttons(["Day up", "Week up"])
        self.enable_buttons(["Day down", "Week down"])

        description, title = await self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=COLOR_Default,
                    description=description,
                    title=title),
            view=self
            )
        

class Leaderboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 


    @app_commands.command(description="Display a leaderboard of a selected stat.")
    @app_commands.describe(stat = "Stat of the leaderboard.",
                            days = "Number of days the period of time has (by default 7).",
                        page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
    async def leaderboard(self, interaction: discord.Interaction, stat: str, days: app_commands.Range[int, 1, database.dbDaysLimit] = 7, page: int = 1):
        #Verification
        correct = await methods.checks(interaction)
        if not correct:
            return

        if page == 0:
            await interaction.response.send_message("I mean on the one hand I appreciate people looking for bugs but on the other hand... it's page 0, what did you expect?", ephemeral=True)
            return

        view = LeaderboardView(self.bot, interaction.user, stat, days, page)

        #Contents of message
        await interaction.response.defer()
        description, title = await view.getData(page, stat, days)
        if not description:
            await interaction.followup.send(title, ephemeral=True)
            # await interaction.response.send_message(title, ephemeral=True)
            return
        
        embed = discord.Embed(
                color=COLOR_Default,
                description=description,
                title=title)
        
        await interaction.followup.send(embed=embed, view=view)
        view.message = await interaction.original_response()
        

    @leaderboard.autocomplete('stat')
    async def leaderboard_autocomplete(self, interaction: discord.Interaction, current: str):

        stats = sorted([
            'Average BPM',
            'Average best combo',
            'Netscores',
            'Average OPB',
            'Average OPM',
            'Average SPM',
            'Blocked%',
            'Sent lines',
            'Time played',
            'Power',
            'Efficiency',
            'Combo count (13)',
            'Combo count (>10)',
        ])
        return [
            app_commands.Choice(name=stat, value=stat)
            for stat in stats if current.lower() in stat.lower()
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))
    print(f"Loaded /leaderboard command.")