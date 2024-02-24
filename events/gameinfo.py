import discord
from discord.ext import commands, tasks
import sys, os
sys.path.append('../c2-stats-bot')
from settings import admins
from datetime import datetime
import json

class Game_Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot: commands.Bot = bot 
        self.messages = []
        self.editor.start()

    def cog_unload(self):
        self.editor.cancel()

    @tasks.loop(seconds=10)
    async def editor(self):
        for message in self.messages:
            message: discord.Message
            await message.edit(content=f"{datetime.now()}")

    @editor.before_loop
    async def before_printer(self):
        try:
            with open("files/online_messages.json", 'r') as f:
                messages = json.load(f)
        except FileNotFoundError:
            await self.bot.wait_until_ready()
            return

        for message_data in messages:
            channel = self.bot.get_channel(message_data.get('channel_id')) or await self.bot.fetch_channel(message_data.get('channel_id'))
            message = await channel.fetch_message(message_data.get('message_id'))
            self.messages.append(message)

        await self.bot.wait_until_ready()
        
    @commands.check(lambda ctx : ctx.author.name in admins)
    @commands.command()
    async def create_online_message(self, ctx: commands.Context):
        message = await ctx.send(f"Online message.")
        self.messages.append(message)

        try:
            print(1)
            with open("files/online_messages.json", 'r') as f:
                msgs = json.load(f)
            print(2)
        except FileNotFoundError:
            msgs = []

        msgs.append({
            'channel_id': message.channel.id,
            'message_id': message.id
        })

        with open("files/online_messages.json", 'w') as f:
            json.dump(msgs, f)
    
    
async def setup(bot: commands.Bot):
    await bot.add_cog(Game_Info(bot))
    print(f"Loaded Game_Info event.")