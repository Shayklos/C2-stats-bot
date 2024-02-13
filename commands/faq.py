import discord
from discord import app_commands
from discord.ext import commands
import sys, os
from os import sep
sys.path.append(f'..{sep}c2-stats-bot')
from settings import admins
from textwrap import dedent

aliases = {
    'webmaster' : ['web', 'website', 'update', 'updates'],
    'mac' : ['macos'],
    'patch' : ['patches', 'mod'],
    'help' : [],
    'simon' : ['c2developer', 'c2devs', 'c2dev', 'dev', 'devs', 'developer'],
    'c1soundtrack' : ['c1ost', 'c1music', 'c1songs'],
}

class FAQ_Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 

    @commands.group()
    async def faq(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            command = self.bot.get_command('faq help')
            ctx.command = command
            ctx.invoked_subcommand = command
            await self.bot.invoke(ctx)

    @faq.command(aliases = aliases['help'])
    async def help(self, ctx: commands.Context):
        s = ""
        for command in aliases.keys():
            s += f"/faq {command}{' '*(20 - len(command))}{aliases.get(command)}\n"
        await ctx.reply(dedent(s), ephemeral = True)
        
    @faq.command(aliases = aliases['webmaster'])
    async def webmaster(self, ctx: commands.Context):
        await ctx.reply(dedent("""
            Simon, Cultris II developer, has stated he will update the game only after the game has a webmaster.
            Anyone can apply to be one, although this would be a long term job with no pay. Contact Simon via email: `de@iru.ch`"""))
            
    @faq.command(aliases = aliases['simon'])
    async def simon(self, ctx: commands.Context):
        await ctx.reply(dedent("""
            Cultris II only developer is Simon Felix. The only way to get in touch with Simon is via email: `de@iru.ch`"""))       
        
        
    @faq.command(aliases = aliases['mac'])
    async def mac(self, ctx: commands.Context):
        await ctx.reply(dedent("""
            There's no official support for macOS.
            However, some users have reported they were able to play using external software, check:
            https://discord.com/channels/202843125633384448/516686648201707548/1182624707716055040
            https://discord.com/channels/202843125633384448/516689168223567872/1042891393019953172"""))

    @faq.command(aliases = aliases['patch'])
    async def patch(self, ctx: commands.Context):
        await ctx.reply(dedent("""
            The Cultris II patch made by Def, significantly improves the game's performance.
            [You can download it here](https://github.com/zDEFz/c2-patch). There's a video in the description with indications in how to install the patch (it's easy!). This patch also allows disabling some ingame sounds, for additional performance gain."""))

    @faq.command(aliases = aliases['c1soundtrack'])
    async def c1soundtrack(self, ctx: commands.Context):
        await ctx.reply(dedent("""
            [Here's a list of the songs in Cultris I](https://docs.google.com/spreadsheets/d/1MPaLgEnlx9bNBmmwzxY0UeiotZ7LZ8VXz64qYdMU24I)."""))
        
    
    ##FAQ_END
    
    
async def setup(bot: commands.Bot):
    await bot.add_cog(FAQ_Commands(bot))
    print(f"Loaded /faq command.")
