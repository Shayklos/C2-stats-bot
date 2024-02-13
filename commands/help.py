import discord
from discord import app_commands
from discord.ext import commands
from discord.ui.item import Item
from typing import Any
import sys
from os import sep
sys.path.append(f'..{sep}c2-stats-bot')
from logger import *
import methods

HELP = {
                                        'Commands' : 
"""***/stats*** *[username] [days] [minutes]* : Shows stats of a user in the last *[days]* days and *[minutes]* minutes. By default, it will use your Discord display name as username, and in 7 days. If you can't find a user, try with an old username.

***/legacystats*** *[username]* : Shows all-time stats of an user. By default, it will use your Discord display name as username. If you can't find a user, try with an old username.

***/leaderboard*** *[stat] [page] [days]* : Displays a leaderboard of a stat. Let Discord autocomplete show you what [stat] parameter can you choose. [page] can be negative to sort backwards.

***/rankings *** *[page]* : Current rank/scores. Doesn't work too well, specially at the end of the leaderboard. I've disabled negative page numbers for this reason. 

***/weeklybest*** : Shows a top 5 on SPM rounds and top 5 cheese times in the last 7 days. **Feel free to suggest things to add here**.

***/online*** : Shows a list of current players online.

***/challenges*** *[challenge]* : Displays stats of a singleplayer challenge (Maserati, Survivor, Swiss Cheese...) of a user.

***/rounds*** *[username]* : Displays a per-round stats table of a user. 

***/help*** *[about]* : Displays helpful information about the bot or the stats it calculates.

Feel free to suggest additions/report bugs.""",

                                        'OPM/OPB' : 
"""OPM stands for Output per minute. The way to calculate is (linesSent + linesBlocked)/playDuration.
OPB stands for Output per block. The way to calculate is (lineSent + linesBlocked)/blocksPlaced.""",

                                        'Power' :
"""The amount of lines a player sends depends on the amount of players alive. Therefore, players will send more lines in bigger rooms. 'Power-2' is a stat that tries to give a player a score on their performance regardless of the size of the rooms they played in. The way this is calculated is using the following table, which represents the average OPM in the last 10 years for every roomsize:
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
`37.8883647435868 * OPM/roomsize_value`

For other roomsizes, the following formula is used:
`37.8883647435868 * OPM/(3*roomsize + 29.4)`

Power can be interpreted as average OPM, if a player had played only 1v1s.
Power shown in `/stats` and `/leaderboard Power` is the average achieved in the range selected, not counting roomsize = 1.""",
                                        'Efficiency' :
"""
Efficiency is Power per block. It could be interpreted as the amount of lines a player sends and blocks per block, if all matches were played on 1v1. 
It's calculated using the following table:
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
`37.8883647435868 * OPB / roomsize_value`

For other roomsizes, the following formula is used:
`37.8883647435868 * OPB/(3*roomsize + 29.4)`

Efficiency shown in `/stats` and `/leaderboard Efficiency` is the average achieved in the range selected, not counting roomsize = 1.

"""
}

ABOUTS = list(HELP) #keys of the dictionary       

class Help(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot 

    @app_commands.command(description="Descriptions of current commands.")
    async def help(self, interaction: discord.Interaction, about: str = 'Commands'):
        about = about if about in ABOUTS else 'Commands'
        msg = HELP[about]

        await interaction.response.send_message(msg, ephemeral = interaction.user.name != 'shayklos')

    @help.autocomplete('about')
    async def help_autocomplete(self, interaction: discord.Interaction, current: str):

        return [
            app_commands.Choice(name=about, value=about)
            for about in sorted(ABOUTS) if current.lower() in about.lower()
        ]


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
    print(f"Loaded /help command.")
    

if __name__ == '__main__':
    #Checks Discord limitation (2000 characters per message) is not reached.
    for about in ABOUTS:
        print(f'{about:<10} {len(HELP[about]):<6}')
        assert len(HELP[about]) <= 2000
            