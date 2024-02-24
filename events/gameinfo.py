import discord
from discord import app_commands
from discord.ext import commands, tasks
import sys, os
sys.path.append('../c2-stats-bot')
from settings import admins
from textwrap import dedent
from datetime import datetime

"""Idea is to look into tasks.loop to edit periodically a msg. This is an example for the docs"""
class Game_Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot: commands.Bot = bot 
        self.messages = []
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=5.0)
    async def printer(self):
        for message in self.messages:
            message: discord.Message
            await message.edit(content=f"{datetime.now()}")

    @printer.before_loop
    async def before_printer(self):
        print('waiting...')
        await self.bot.wait_until_ready()

    @commands.command()
    async def create_online_message(self, ctx: commands.Context):
        if ctx.author.name not in admins:
            return
        
        print("/ping was called by", ctx.author.name)
        message = await ctx.send(f"Online message.")
        self.messages.append(message)

    
    
async def setup(bot: commands.Bot):
    await bot.add_cog(Game_Info(bot))
    print(f"Loaded Game_Info event.")