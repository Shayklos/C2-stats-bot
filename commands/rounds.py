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
from settings import powerTable

class RoundsView(CultrisView):

    def __init__(self, bot, author, user, userId):
        super().__init__(bot=bot, author=author)
        self.command = '/rounds'
        
        self.interactionUser = author
        self.user = user 
        self.userId = userId
        self.page = 0
    

    async def generate_data(self):
        def maxcolumn(i, l):
            return max([len(e[i]) for e in l])
        
        query = self.bot.db.execute("""select 
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


    from rounds join matches on rounds.roundid=matches.roundid where userid = ? order by start desc""", (self.userId,))

        header = ["Start","Place","BPM","Cmb","Power","Effi.", "SPM","OPM","Block%","Time\n"]
        lines = [header]
        pages = []
        count = 0
        diff = 1
        async with query as rounds:
            async for round in rounds: 
                try:
                    if 1<round["roomsize"]<10:
                        power = powerTable.get(2) * 60*(round['sent']+round['blocked'])/(round['time'] * powerTable.get(round["roomsize"]))
                        ppb = powerTable.get(2) * 60*(round['sent']+round['blocked'])/(round['blocks'] * powerTable.get(round["roomsize"]))
                    else:
                        power = powerTable.get(2) * 60*(round['sent']+round['blocked'])/(round['time'] * (3*powerTable.get(round["roomsize"]) + 29.4))
                        ppb = powerTable.get(2) * 60*(round['sent']+round['blocked'])/(round['blocks'] * (3*powerTable.get(round["roomsize"]) + 29.4))

                    lines.append([round['start'][5:16],
                        f"{round['place']}/{round['roomsize']}",
                        f"{60*round['blocks']/round['time']:.1f}",
                        f"{round['cmb']}",
                        f"{power:.1f}",
                        f"{ppb:.1f}%",
                        f"{60*round['sent']/round['time']:.1f}",
                        f"{60*(round['sent']+round['blocked'])/round['time']:.1f}",
                        f"{100*round['blocked'] / round['got']:.1f}",
                        f"{round['time']:.1f}\n"
                    ])
                    count += 1
                except:
                    pass
                
                if count%20==0:
                    result = "```diff\n"
                    for line in lines: 
                        if diff == 1:
                            result += '+'
                            diff *= -1
                        else:
                            result += '-'
                            diff *= -1
                        for i, element in enumerate(line):
                            if element[-1] != '\n':
                                result += element + " "*(maxcolumn(i, lines)-len(element)+3)
                            else:
                                result += element

                    pages.append(f"Rounds of {self.user}"+result+'```')
                    lines = [header]
                    diff = 1
            return pages

    @discord.ui.button(label="Page down", row = 1, style=discord.ButtonStyle.primary, emoji="⬅️") 
    async def page_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        # self.logButton(interaction, button)
        self.page -= 1
        await interaction.response.edit_message(content = self.data[self.page+1],
            view=self
            )

    @discord.ui.button(label="Page up", row = 1, style=discord.ButtonStyle.primary, emoji="➡️") 
    async def page_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        # self.logButton(interaction, button)
        self.page += 1
        await interaction.response.edit_message(content = self.data[self.page+1],
            view=self
            )


 

class Rounds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 


    @app_commands.command(description="Display round stats of a certain player.")
    @app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
    @app_commands.guild_only()
    async def rounds(self, interaction: discord.Interaction, username: str = None):
        #Verification
        correct = await methods.checks(interaction)
        if not correct:
            return

        if not username:
            username = interaction.user.display_name

        ratio, userId, user = await database.fuzzysearch(self.bot.db, username.lower())
        msg = None if ratio == 100 else f"No user found with name \'{username}\'. Did you mean \'{user}\'?"
        
        view = RoundsView(self.bot, interaction.user, user, userId)
        view.data = await view.generate_data()
        
        await interaction.response.send_message(view.data[0], view=view)
        view.message = await interaction.original_response()
        

async def setup(bot: commands.Bot):
    await bot.add_cog(Rounds(bot))