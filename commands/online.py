import discord
from discord import app_commands
from discord import ui
from discord.ext import commands
import sys
from os import sep
sys.path.append(f'..{sep}c2-stats-bot')
import database, methods
from bot import developerMode
from settings import COLOR_Default

class Online(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 


    @app_commands.command(description="Shows which users are online right now.")
    async def online(self, interaction: discord.Interaction):
        players = await database.getPlayersOnline()

        view = ui.LayoutView()
        title = ui.TextDisplay("**Players Online**")
        description = ui.TextDisplay(players)
        container = ui.Container(title, description, accent_color=COLOR_Default)
        
        if not interaction.guild and (developerMode or interaction.user.name in database.admins):
            container.add_item(ui.Separator())

            extradata = await database.getPlayersWhoPlayedRecently(self.bot.db)
            msg = "Players who played in the last hour: "
            for player in extradata.get('players'):
                msg += f"**{player[0]}**, "
            msg = msg[:-2]
            msg += "\nGuests who played in the last hour: "
            for guest in extradata.get('guests'):
                msg += f"**{guest[0]}**, "
            
            container.add_item(ui.TextDisplay(msg[:-2]))

        view.add_item(container)
        await interaction.response.send_message(view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Online(bot))
    print(f"Loaded /online command.")