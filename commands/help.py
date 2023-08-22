import discord
from discord import app_commands
from discord.ext import commands
from discord.ui.item import Item
from typing import Any
import sys
sys.path.append('../c2-stats-bot')
from logger import *
import methods

class Help(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot 

    @app_commands.command(description="Descriptions of current commands.")
    async def help(self, interaction: discord.Interaction, about: str = 'Commands'):
        correct = await methods.checks(interaction)
        if not correct:
            return
        
        about = about if about in ['Commands', 'OPM/OPB', 'Power'] else 'Commands'

        match about:
            case 'Power':
                msg = """The amount of lines a player sends depends on the amount of players alive. Therefore, players will send more lines in bigger rooms. 'Power' is a stat that tries to give a player a score on their performance regardless of the size of the rooms they played in. The way this was done is by calculate the average OPM in the last 10 years for every roomsize.
For roomsizes between 2 and 9 Power in a round is calculated using the following table
```
roomsize: value
2: 37.8883647435868, 
3: 35.4831455255647, 
4: 40.1465889629567, 
5: 44.2602184213111, 
6: 48.575338292518, 
7: 50.649550305342, 
8: 51.9969119509592, 
9: 56.306414280463
```
with the following formula:
`(10/3) * OPM/roomsize_value`

For other roomsizes, the following formula is used:
`10 * OPM/(roomsize + 9.8)`

Power shown in `/stats` and `/leaderboard Power` is the average achieved in the range selected, not counting roomsize = 1. 
            """

            case 'OPM/OPB':
                msg = """OPM stands for Output per minute. The way to calculate is (linesSent + linesBlocked)/playDuration.
OPB stands for Output per block. The way to calculate is (lineSent + linesBlocked)/blocksPlaced."""

            case 'Commands':
                msg = """***/stats*** *[username] [days]* : Shows stats of a user in the last *[days]* days. By default, it will use your Discord display name as username, and in 7 days. If you can't find a user, try with an old username.

***/legacystats*** *[username]* : Shows all-time stats of an user. By default, it will use your Discord display name as username. If you can't find a user, try with an old username.

***/weeklybest*** : Shows a top 5 on SPM rounds and top 5 cheese times in the last 7 days. **Feel free to suggest things to add here**.

***/online*** : Shows a list of current players online.

***/leaderboard*** *[stat] [page] [days]* : Displays a leaderboard of a stat. Let Discord autocomplete show you what [stat] parameter can you choose. [page] can be negative to sort backwards.

***/rankings *** *[page] [fast]* : Current rank/scores. Doesn't work too well, specially at the end of the leaderboard. I've disabled negative page numbers for this reason. If `fast = True` it will display values stored in the database. If `fast = False` it will request them from gewaltig instead. No matter if this parameter is True or False, the positions on the leaderboard will be the same. 

***/challenges*** *[challenge]* : Displays stats of a singleplayer challenge (Maserati, Survivor, Swiss Cheese...).

Feel free to suggest additions/report bugs."""
                
        await interaction.response.send_message(msg, ephemeral = interaction.user.name != 'shayklos')

    @help.autocomplete('about')
    async def help_autocomplete(self, interaction: discord.Interaction, current: str):

        abouts = sorted([
            'Commands',
            'OPM/OPB',
            'Power'
        ])
        return [
            app_commands.Choice(name=about, value=about)
            for about in abouts if current.lower() in about.lower()
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))