import discord
from discord import app_commands
from discord.ext import commands
import sys, os
sys.path.append('../c2-stats-bot')
from settings import admins


class DevCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 


    @commands.command()
    async def ping(self, ctx: commands.Context):
        if ctx.author.name not in admins:
            return
        
        print("/ping was called by", ctx.author.name)
        await ctx.send(f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms")


    @commands.command()
    async def reload(self, ctx: commands.Context, command: str = 'all'): 
        """
        Reloads all commands in the commands folder without needing to restart the bot. 
        """
        
        if ctx.author.name not in admins:
            return
        
        print("/reload was called by", ctx.author.name)

        if command == 'all':
            for extension in ["".join(('commands.', extension[:-3])) for extension in os.listdir('commands') if extension[-3:] == '.py']:
                await self.bot.reload_extension(extension)

        else:
            await self.bot.reload_extension('commands.' + command)


        await ctx.message.add_reaction("👍")


async def setup(bot: commands.Bot):
    await bot.add_cog(DevCommands(bot))
    print("Dev commands were loaded.")