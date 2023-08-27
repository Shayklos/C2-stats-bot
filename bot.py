import discord
from discord.ext import commands

from os import listdir, getenv
from dotenv import load_dotenv

import aiosqlite

developerMode = False

load_dotenv()
TOKEN = getenv('DISCORD_TOKEN')
GUILD_ID = getenv('DISCORD_GUILD_ID')

class CultrisBot(commands.Bot):
    def __init__(self, intents: discord.Intents):
        super().__init__(command_prefix = '/', intents = intents, activity=discord.Game(name="Cultris II"))

    async def setup_hook(self):
        
        #Loads all commands in 'commands' folder
        for command in ["".join(('commands.', command[:-3])) for command in listdir('commands') if command[-3:] == '.py']:
            await self.load_extension(command)
            print(f"Loaded /{command[9:]} command.")

        if developerMode:
            #Makes me have to wait less in my testing guild
            self.tree.copy_global_to(guild=discord.Object(id=GUILD_ID))
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))
        await self.tree.sync(guild=None)
        self.db = await aiosqlite.connect(r"files/cultris.db")
        self.db.row_factory = aiosqlite.Row

        print("Bot is ready!")


intents = discord.Intents.default()
intents.message_content = True

cultrisBot = CultrisBot(intents = intents)

if __name__ == '__main__':
    if developerMode:
        print("DEVELOPER MODE")
    cultrisBot.run(TOKEN)