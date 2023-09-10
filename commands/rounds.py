import discord
from discord import app_commands
from discord.ext import commands
from discord.ui.item import Item
from typing import Any
import asyncio
import csv
from pytz import timezone
from datetime import datetime
import sys
sys.path.append('../c2-stats-bot')
from logger import *
import database, methods
from CultrisView import CultrisView
from settings import powerTable, multiplier, admins

class RoundsView(CultrisView):

    def __init__(self, bot, author, user, userId):
        super().__init__(bot=bot, author=author)
        self.command = '/rounds'
        
        self.interactionUser = author
        self.cultrisUsername = user 
        self.userId = userId
        self.page = 0
    

    def codeblocksFormat(self, lines: list[list[str]], header: list[str] = None, spacing: int = 3):
        """
        Transforms a list of values into an aligned text table, assuming that the font used is monospaced
        """
        page = [header, *lines] if header else lines
        
        alignPoints = []
        for i in range(len(header)):
            alignPoints.append(
                max([len(line[i]) for line in page]) # biggest value in column i, used for aligning purposes
            )
            
        lineColorToggle = True
        result = "```diff\n"
        for line in page: 
            result += '+' if lineColorToggle else '-' #The purpose of these is to be easier for the human eye to read, as they change the color of a whole line
            lineColorToggle = not lineColorToggle
            for i, element in enumerate(line):
                if element[-1] == '\n':
                    result += element
                else:
                    result += element + " "*(alignPoints[i] - len(element) + spacing)

        return result + "```"


    async def generate_data(self):
        query = self.bot.db.execute("""
            select 
                start,
                place,
                roomsize,
                linesGot as got,
                linesSent as sent,
                linesBlocked as blocked,
                blocks,
                maxCombo as cmb,
                playDuration as time 
        from rounds join matches on rounds.roundid=matches.roundid 
        where userid = ? 
        order by start desc""", (self.userId,))

        header = ["Start","Place","BPM","Cmb","Power","Effi.", "SPM","OPM","Block%","Time\n"]
        lines = []
        pages = []
        count = 0
        async with query as rounds:
            async for round in rounds: 
                output = round["sent"] + round["blocked"]

                if not round["blocks"] or not round["time"]:
                    continue

                if 1<round["roomsize"]<10:
                    power = 60  * multiplier[round["roomsize"]] * output / round["time"]
                    ppb   = 100 * multiplier[round["roomsize"]] * output / round["blocks"]
                else:
                    power = 60  * powerTable.get(2) * output/(round['time']   * (3*round["roomsize"] + 29.4))
                    ppb   = 100 * powerTable.get(2) * output/(round['blocks'] * (3*round["roomsize"] + 29.4))

                blocked   = 100 * round['blocked']/round['got'] if round['got'] else 0

                lines.append([
                    #["Start","Place","BPM","Cmb","Power","Effi.", "SPM","OPM","Block%","Time\n"]
                    round['start'][5:],
                    f"{round['place']}/{round['roomsize']}",
                    f"{60 * round['blocks']/round['time']:.1f}",
                    f"{round['cmb']}",
                    f"{power:.1f}",
                    f"{ppb:.1f}%",
                    f"{60 * round['sent']/round['time']:.1f}",
                    f"{60 * output /round['time']:.1f}",
                    f"{blocked:.1f}%",
                    f"{round['time']:.1f}\n"
                ])
                
                count += 1
                
                if not count%20:
                    pages.append(self.codeblocksFormat(lines, header))
                    lines = []
        print(3)
        return pages 
    

    async def generate_downloadable(self):
        #todo cheese rooms, ruleset dict, team dict, etc
        query = self.bot.db.execute("""
            select 
                start,
                place,
                roomsize,
                linesGot as got,
                linesSent as sent,
                linesBlocked as blocked,
                blocks,
                maxCombo as cmb,
                playDuration as time, 
                ruleset,
                cheeserows,
                team
        from rounds join matches on rounds.roundid=matches.roundid 
        where userid = ? 
        order by start desc""", (self.userId,))

        data = [
                ['Start', 'Place', 'Roomsize', 'maxCombo', 'blocksPlaced', 
                'linesSent', 'linesBlocked', 'linesGot', 'Blocked%', 'BPM', 
                'SPM','SPB%','OPM','OPB%','Power','Efficiency%',
                'playDuration']
            ]
        async with query as rounds:
            async for round in rounds: 
                output = round["sent"] + round["blocked"]

                if not round["blocks"] or not round["time"]:
                    continue

                if 1<round["roomsize"]<10:
                    power = 60  * multiplier[round["roomsize"]] * output / round["time"]
                    ppb   = 100 * multiplier[round["roomsize"]] * output / round["blocks"]
                else:
                    power = 60  * powerTable.get(2) * output/(round['time']   * (3*round["roomsize"] + 29.4))
                    ppb   = 100 * powerTable.get(2) * output/(round['blocks'] * (3*round["roomsize"] + 29.4))

                blocked   = 100 * round['blocked']/round['got'] if round['got'] else 0

                data.append([
                    # Start, place, roomsize, maxCombo, blocksPlaced, linesSent, linesBlocked, linesGot, Blocked%, BPM
                    # SPM, SPB, OPM, OPB, Power, Efficiency, playDuration
                    round["start"],
                    round['place'],
                    round['roomsize'],
                    round['cmb'],
                    round['blocks'],
                    round['sent'],
                    round['blocked'],
                    round['got'],
                    blocked,
                    60 * round['blocks']/round['time'],
                    60 * round['sent']/round["time"],
                    100 * round['sent']/round['blocks'],
                    60 * output/round["time"],
                    100 * output/round['blocks'],
                    power,
                    ppb,
                    round['time'],

                ])
                
        filename = f"files/userdata/rounds/{self.cultrisUsername}_{datetime.now(tz = timezone('UTC')).strftime('%Y_%m_%d')}.csv"
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f, delimiter = ';')
            writer.writerows(data)
        self.downloadable = discord.File(filename)
        return


    @discord.ui.button(label="Page down", row = 0, style=discord.ButtonStyle.primary, emoji="⬅️") 
    async def page_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page -= 1
        await interaction.response.edit_message(content = f"Rounds of {self.cultrisUsername}" + self.data[self.page],
            view=self
            )

    @discord.ui.button(label="Page up", row = 0, style=discord.ButtonStyle.primary, emoji="➡️") 
    async def page_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page += 1
        await interaction.response.edit_message(content = f"Rounds of {self.cultrisUsername}" + self.data[self.page],
            view=self
            )
        
    @discord.ui.button(label="Download", row = 1, style=discord.ButtonStyle.primary, emoji="⬇️") 
    async def download(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        button.disabled = True
        await self.generate_downloadable()
        await interaction.channel.send(file = self.downloadable)
        await interaction.response.edit_message(view = self)


 

class Rounds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 

    def cooldown(interaction: discord.Interaction):
        #One call every two minutes, Ignores cooldown for admins
        if interaction.user.name in admins:
            return None 
        return app_commands.Cooldown(1, 120)


    @app_commands.command(description="Display round stats of a certain player.")
    @app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
    @app_commands.checks.dynamic_cooldown(cooldown, key = lambda i: (i.guild_id, i.user.id))
    async def rounds(self, interaction: discord.Interaction, username: str = None):
        #Verification
        correct = await methods.checks(interaction)
        if not correct:
            return

        if not username:
            username = interaction.user.display_name

        ratio, userId, cultrisUsername = await database.fuzzysearch(self.bot.db, username.lower())
        msg = None if ratio == 100 else f"No user found with name \'{username}\'. Did you mean \'{cultrisUsername}\'?"

        view = RoundsView(self.bot, interaction.user, cultrisUsername, userId)
        view.data = await view.generate_data()
        
        await interaction.response.send_message(f"Rounds of {cultrisUsername}" + view.data[0], view=view)
        view.message = await interaction.original_response()

    
    
    @rounds.error #Cooldown handling
    async def roundsError(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"/rounds can only be used once every 2 minutes! Try again in {int(error.retry_after)}s.", ephemeral=True)
        

async def setup(bot: commands.Bot):
    await bot.add_cog(Rounds(bot))


if __name__ == "__main__":
    import aiosqlite

    async def main():
        db = await aiosqlite.connect("files/cultrisTest.db")
        db.row_factory = aiosqlite.Row
        class Bot():
            def __init__(self):
                self.db = db

        bot = Bot()
        view = RoundsView(bot, 0, "Shay", 5840)
        pages = await view.generate_data()

        print(pages[0])

    asyncio.run(main())