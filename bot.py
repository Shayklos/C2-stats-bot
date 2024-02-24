import discord
from discord.ext import commands

from os import listdir, getenv
from os.path import join
from dotenv import load_dotenv

import aiosqlite

developerMode = True

load_dotenv() 
TOKEN = getenv('DISCORD_TOKEN') if not developerMode else getenv('DISCORD_TEST_TOKEN')
PREFIX = '/' if not developerMode else '-'
GUILD_ID = getenv('DISCORD_GUILD_ID')

class CultrisBot(commands.Bot):
    def __init__(self, intents: discord.Intents):
        super().__init__(command_prefix = PREFIX, intents = intents, activity=discord.Game(name="Cultris II"))

    async def setup_hook(self):
        
        #Loads all commands in 'commands' folder
        for command in ["".join(('commands.', command[:-3])) for command in listdir('commands') if command[-3:] == '.py']:
            await self.load_extension(command)

        #Loads all events in 'events' folder
        for command in ["".join(('events.', command[:-3])) for command in listdir('events') if command[-3:] == '.py']:
            await self.load_extension(command)

        self.db = await aiosqlite.connect(join("files", "cultris.db"))
        self.db.row_factory = aiosqlite.Row

        print("Bot is ready!")


intents = discord.Intents.default()
intents.message_content = True

cultrisBot = CultrisBot(intents = intents)


if __name__ == '__main__':
    if developerMode:
        print("DEVELOPER MODE")
    cultrisBot.run(TOKEN)