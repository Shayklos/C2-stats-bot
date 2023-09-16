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



    @commands.command(aliases = ['r', 'rl'])
    async def reload(self, ctx: commands.Context, command: str = 'all'): 
        """
        Reloads all commands in the commands folder without needing to restart the bot. 
        """
        
        if ctx.author.name not in admins:
            return
        
        print("/reload was called by", ctx.author.name)

        if command == 'all':
            for extension in ["".join(('commands.', extension[:-3])) for extension in os.listdir('commands') if extension[-3:] == '.py']:
                try:
                    await self.bot.reload_extension(extension)
                except:
                    await self.bot.load_extension(extension)

        else:
            try:
                await self.bot.reload_extension('commands.' + command)
            except:
                await self.bot.load_extension('commands.' + command)


        await ctx.message.add_reaction("👍")



    @commands.command()
    async def disable(self, ctx: commands.Context, command: str): 
        """
        Disables a command/ all commands
        """
        
        if ctx.author.name not in admins:
            return
        
        print("/disable was called by", ctx.author.name)

        if command == 'all':
            for extension in ["".join(('commands.', extension[:-3])) for extension in os.listdir('commands') if extension[-3:] == '.py']:
                await self.bot.unload_extension(extension)

        else:
            await self.bot.unload_extension('commands.' + command)


        await ctx.message.add_reaction("👍")



    @commands.command()
    async def change_status(self, ctx: commands.Context, status: str): 
        """
        Changes bot status (online, idle, dnd, offline)
        """
        
        if ctx.author.name not in admins:
            return
        
        print("/change_status was called by", ctx.author.name)

        match status:
            case "online":
                await self.bot.change_presence(status=discord.Status.online)
            case "offline":
                await self.bot.change_presence(status=discord.Status.invisible)
            case "idle":
                await self.bot.change_presence(status=discord.Status.idle)
            case "dnd":
                await self.bot.change_presence(status=discord.Status.dnd)
            case other:
                await ctx.message.add_reaction("👎")
                return
            
        await ctx.message.add_reaction("👍")



    @commands.command()
    async def commands(self, ctx: commands.Context): 
        """
        Displays list of dev commands
        """
        
        if ctx.author.name not in admins:
            return
        
        print("/commands was called by", ctx.author.name)

        await ctx.reply("""ping
reload [command | all]
disable [command |all]
change_status [online | offline | idle | dnd]
commands
""", ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(DevCommands(bot))
    print("Dev commands were loaded.")