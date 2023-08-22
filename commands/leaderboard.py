import discord
from discord import app_commands
from discord.ext import commands
from discord.ui.item import Item
from typing import Any
import sys
sys.path.append('../c2-stats-bot')
from logger import *
import database, methods


class LeaderboardView(discord.ui.View):

    def __init__(self, bot, author, stat, days, page):
        super().__init__(timeout=120)
        self.bot = bot
        self.interactionUser = author
        self._stat = stat
        self.page = page
        self.days = days
        self.command = '/leaderboard'

    async def on_timeout(self):
        print("timeout")
        for item in self.children:
            item.style = discord.ButtonStyle.grey
            item.disabled = True
        await self.message.edit(view=self)


    async def interaction_check(self, interaction: discord.Interaction):
        #checks if user who used the button is the same who called the command
        if interaction.user == self.interactionUser:
            return True
        else:
            await interaction.user.send("Only the user who called the command can use the buttons.")
    

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: Item[Any]) -> None:
        print(error)
        await interaction.user.send("Something went horribly wrong. Uh oh.")


    def logButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        log(f"{interaction.user.display_name} ({interaction.user.name}) in {self.command} pressed [{button.label}]","files/log_discord.txt")


    def enable_buttons(self, list):
        for item in self.children:
            if item.label in list:
                item.disabled = False


    def disable_buttons(self, list):
        for item in self.children:
            if item.label in list:
                item.disabled = True


    def getData(self, page, stat, days, pageSize = database.embedPageSize):
        match stat:
            case 'Blocked%':
                data = database.getBlockedPercent(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average percentage of blocked lines ({days} days)"

            case 'Average OPB':
                data = database.getavgOPB(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Output per block ({days} days)"

            case 'Average OPM':
                data = database.getavgOPM(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Output per minute ({days} days)"

            case 'Average BPM':
                data = database.getavgBPM(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Blocks per minute ({days} days)"

            case 'Average SPM':
                data = database.getavgSPM(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Sent per minute ({days} days)"

            case 'Time played':
                data = database.getTimePlayed(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize, isTime = True)
                title=f"Most active players ({days} days)" if page > 0 else f"Least active players ({days} days)"

            case 'Sent lines':
                data = database.getSent(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Total lines sent ({days} days)"
                
            case 'Netscores':
                data = database.getNetscores(self.bot.db, days=days) if 1 < days <= 7 else None
                page = 1 if data and pageSize*(page - 1) > len(data) else page
                if data:
                    description=methods.getPage(page, data, pageSize = pageSize)
                else:
                    description = "Use /stats to see 1 day Netscores." if days == 1 else "Netscores data is only supported for up to a week."

                title=f"Netscores ({days} days)"

            case 'Average best combo':
                data = database.getCombos(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average best combo ({days} days)"

            case 'Power':
                data = database.getPower(self.bot.db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Power ({days} days)"

            case other:
                return None, None
        
        return description, title


    @discord.ui.button(label="Week down", row = 0, style=discord.ButtonStyle.primary, emoji="⏬") 
    async def week_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.days = max(1, self.days-7)
        if self.days == 1:
            self.disable_buttons(["Day down", "Week down"])
        self.enable_buttons(["Day up", "Week up"])

        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
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

        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
                    description=description,
                    title=title),
            view=self
            )

    @discord.ui.button(label="Page down", row = 1, style=discord.ButtonStyle.primary, emoji="⬅️") 
    async def page_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page = -1 if self.page == 1 else self.page - 1
        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
                    description=description,
                    title=title),
            view=self
            )

    @discord.ui.button(label="Page up", row = 1, style=discord.ButtonStyle.primary, emoji="➡️") 
    async def page_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page = 1 if self.page == -1 else self.page + 1
        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
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

        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
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

        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
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
    async def leaderboard(self, interaction: discord.Interaction, stat: str, days: app_commands.Range[int, 1, 30] = 7, page: int = 1):
        #Verification
        correct = await methods.checks(interaction)
        if not correct:
            return

        view = LeaderboardView(self.bot, interaction.user, stat, days, page)

        #Contents of message
        description, title = view.getData(page, stat, days)
        if not description:
            await interaction.response.send_message("Did you choose a stat?", ephemeral=True)
            return
        
        embed = discord.Embed(
                color=0x0B3C52,
                description=description,
                title=title)
        
        await interaction.response.send_message(embed=embed, view=view)
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
        ])
        return [
            app_commands.Choice(name=stat, value=stat)
            for stat in stats if current.lower() in stat.lower()
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))