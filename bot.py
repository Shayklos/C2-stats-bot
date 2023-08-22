import discord
from discord.ext import commands

from os import listdir, getenv
from dotenv import load_dotenv

import sqlite3

developerMode = False
load_dotenv()
TOKEN = getenv('DISCORD_TOKEN')
GUILD_ID = getenv('DISCORD_GUILD_ID')

intents = discord.Intents.default()
intents.message_content = True

class CultrisBot(commands.Bot):
    def __init__(self, intents: discord.Intents):
      super().__init__(command_prefix = '/', intents = intents, activity=discord.Game(name="Cultris II"))

    async def setup_hook(self):
        
        for command in ["".join(('commands.', command[:-3])) for command in listdir('commands') if command != '__pycache__']:
            await self.load_extension(command)

        if developerMode:
            self.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        await self.tree.sync(guild=None)
        self.db = sqlite3.connect(r"files/cultris.db")

        print("Ready")


cultrisBot = CultrisBot(intents = intents)

if __name__ == '__main__':
    if developerMode:
        print("DEVELOPER MODE")
    cultrisBot.run(TOKEN)