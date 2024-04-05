import discord
from discord.ext import commands, tasks
from datetime import datetime
import sys
from os.path import join

sys.path.append("../c2-stats-bot")
from settings import admins, COLOR_Default, online_message_frequency
from database import getPlayersOnline, getLiveinfoData
from logger import log
import json


class Game_Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot: commands.Bot = bot
        self.liveinfo = None
        self.messages = []
        self.channels = []
        self.edit_channel_name = True
        self.online_message_editor.start()

    def cog_unload(self):
        self.online_message_editor.cancel()

    @tasks.loop(seconds=online_message_frequency)
    async def online_message_editor(self):
        self.liveinfo = await getLiveinfoData()
        if not self.liveinfo:
            log(
                "Liveinfo endpoint (and likely all endpoints) seems to be down.",
                "error.txt",
            )
            return
        players = await getPlayersOnline(self.liveinfo)

        embed = discord.Embed(
            color=COLOR_Default, description=players, title="Players online"
        )

        last_updated = f"<t:{int(datetime.now().timestamp())}:R>"
        for message in self.messages:
            message: discord.Message
            await message.edit(content=f"Last updated: {last_updated}", embed=embed)

    @tasks.loop(seconds=310) # Hardcoded, there's a ratelimit we're approaching like this
    async def channel_editor(self):
        if not self.edit_channel_name or not self.liveinfo:
            return

        try:
            for channel in self.channels:
                channel: discord.TextChannel
                await channel.edit(name=f"online ({len(self.liveinfo.get('players'))})")
        except discord.errors.Forbidden:
            log(f"Missing `Manage Channels` permisions in channel {channel.name} ({channel.id}) of server {channel.guild.id}.")


    @online_message_editor.before_loop
    async def before_editor(self):
        try:
            with open(join("files", "online_messages.json"), "r") as f:
                messages = json.load(f)
        except FileNotFoundError:
            await self.bot.wait_until_ready()
            return

        for message_data in messages:
            channel = self.bot.get_channel(
                message_data.get("channel_id")
            ) or await self.bot.fetch_channel(message_data.get("channel_id"))
            message = await channel.fetch_message(message_data.get("message_id"))
            self.messages.append(message)
            self.channels.append(channel)

        await self.bot.wait_until_ready()

    @commands.check(lambda ctx: ctx.author.name in admins)
    @commands.command()
    async def create_online_message(self, ctx: commands.Context):
        message = await ctx.send("Online message.")
        self.messages.append(message)

        try:
            with open(join("files", "online_messages.json"), "r") as f:
                msgs = json.load(f)
        except FileNotFoundError:
            msgs = []

        msgs.append({"channel_id": message.channel.id, "message_id": message.id})

        with open(join("files", "online_messages.json"), "w") as f:
            json.dump(msgs, f)

    @commands.check(lambda ctx: ctx.author.name in admins)
    @commands.command()
    async def delete_online_message_connection(self, ctx: commands.Context, id: int):
        try:
            with open(join("files", "online_messages.json"), "r") as f:
                msgs = json.load(f)
        except FileNotFoundError:
            return

        for msg in msgs:
            if id == msg.get("message_id"):
                msgs.remove(msg)

        for message in self.messages:
            if message.id == id:
                self.messages.remove(message)

        with open(join("files", "online_messages.json"), "w") as f:
            json.dump(msgs, f)

    @commands.check(lambda ctx: ctx.author.name in admins)
    @commands.command()
    async def change_online_message_update_frequency(
        self, ctx: commands.Context, seconds: int
    ):
        self.online_message_editor.change_interval(seconds=seconds)

    @commands.check(lambda ctx: ctx.author.name in admins)
    @commands.command()
    async def export_online_messages(self, ctx: commands.Context):
        await ctx.send(file=discord.File(join("files", "online_messages.json")))

    @commands.check(lambda ctx: ctx.author.name in admins)
    @commands.command()
    async def toggleChannelNameEdition(self, ctx: commands.Context):
        self.edit_channel_name = not self.edit_channel_name


async def setup(bot: commands.Bot):
    await bot.add_cog(Game_Info(bot))
    print("Loaded Game_Info event.")
