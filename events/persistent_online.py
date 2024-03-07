import discord
from discord.ext import commands, tasks
from datetime import datetime
import sys
from os.path import join
sys.path.append('../c2-stats-bot')
from settings import admins, COLOR_Default, online_message_frequency
from database import getPlayersOnline
import json

class Game_Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot: commands.Bot = bot 
        self.messages = []
        self.editor.start()

    def cog_unload(self):
        self.editor.cancel()

    @tasks.loop(seconds=online_message_frequency)
    async def editor(self):
        players = await getPlayersOnline()

        embed = discord.Embed(
                color=COLOR_Default,
                description=players,
                title="Players online"
            )
        
        last_updated = f'<t:{int(datetime.now().timestamp())}:R>'

        for message in self.messages:
            message: discord.Message
            await message.edit(content=f"Last updated: {last_updated}", embed=embed)

    @editor.before_loop
    async def before_editor(self):
        try:
            with open(join("files", "online_messages.json"), 'r') as f:
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
            with open(join("files", "online_messages.json"), 'r') as f:
                msgs = json.load(f)
        except FileNotFoundError:
            msgs = []

        msgs.append({
            'channel_id': message.channel.id,
            'message_id': message.id
        })

        with open(join("files", "online_messages.json"), 'w') as f:
            json.dump(msgs, f)
    
    @commands.check(lambda ctx : ctx.author.name in admins)
    @commands.command()
    async def delete_online_message_connection(self, ctx: commands.Context, id: int):
        try:
            with open(join("files", "online_messages.json"), 'r') as f:
                msgs = json.load(f)
        except FileNotFoundError:
            return
        
        for msg in msgs:
            if id == msg.get('message_id'):
                msgs.remove(msg)

        for message in self.messages:
            if message.id == id:
                self.messages.remove(message)

        with open(join("files", "online_messages.json"), 'w') as f:
            json.dump(msgs, f)

    @commands.check(lambda ctx : ctx.author.name in admins)
    @commands.command()
    async def change_online_message_update_frequency(self, ctx: commands.Context, seconds: int):
        self.editor.change_interval(seconds = seconds)

async def setup(bot: commands.Bot):
    await bot.add_cog(Game_Info(bot))
    print(f"Loaded Game_Info event.")