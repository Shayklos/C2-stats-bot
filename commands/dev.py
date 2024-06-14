import aiosqlite
import discord
from discord.ext import commands
import sys
import os
from os import sep
from os.path import join
import json

sys.path.append(f"..{sep}c2-stats-bot")
from settings import admins
from bot import GUILD_ID


class DevCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    def isAdmin(ctx: commands.Context):
        print(f"/{ctx.command} was called by {ctx.author.name}")
        return ctx.author.name in admins

    @commands.command()
    @commands.check(isAdmin)
    async def ping(self, ctx: commands.Context):
        await ctx.send(
            f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms"
        )

    @commands.command(aliases=["r", "rl"])
    @commands.check(isAdmin)
    async def reload(self, ctx: commands.Context, command: str = "all"):
        """
        Reloads all commands in the commands folder without needing to restart the bot.
        """
        if command == "all":
            for extension in [
                "".join(("commands.", extension[:-3]))
                for extension in os.listdir("commands")
                if extension[-3:] == ".py"
            ]:
                try:
                    await self.bot.reload_extension(extension)
                except:
                    await self.bot.load_extension(extension)

        else:
            try:
                await self.bot.reload_extension("commands." + command)
            except:
                await self.bot.load_extension("commands." + command)

        await ctx.message.add_reaction("👍")

    @commands.command(aliases=["re", "rle"])
    @commands.check(isAdmin)
    async def reload_event(self, ctx: commands.Context, command: str = "all"):
        """
        Reloads all events in the commands folder without needing to restart the bot.
        """
        if command == "all":
            for extension in [
                "".join(("events.", extension[:-3]))
                for extension in os.listdir("events")
                if extension[-3:] == ".py"
            ]:
                try:
                    await self.bot.reload_extension(extension)
                except:
                    await self.bot.load_extension(extension)

        else:
            try:
                await self.bot.reload_extension("events." + command)
            except:
                await self.bot.load_extension("events." + command)

        await ctx.message.add_reaction("👍")

    @commands.command()
    @commands.check(isAdmin)
    async def disable(self, ctx: commands.Context, command: str):
        """
        Disables a command/ all commands
        """
        if command == "all":
            for extension in [
                "".join(("commands.", extension[:-3]))
                for extension in os.listdir("commands")
                if extension[-3:] == ".py"
            ]:
                await self.bot.unload_extension(extension)

        else:
            await self.bot.unload_extension("commands." + command)

        await ctx.message.add_reaction("👍")

    @commands.command()
    @commands.check(isAdmin)
    async def change_status(self, ctx: commands.Context, status: str):
        """
        Changes bot status (online, idle, dnd, offline)
        """
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
    @commands.check(isAdmin)
    async def sync(self, ctx: commands.Context):
        """
        Syncs bot commands
        """
        self.bot.tree.copy_global_to(
            guild=discord.Object(id=GUILD_ID)
        )  # Makes me have to wait less in my testing guild
        await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await self.bot.tree.sync(guild=None)

        await ctx.message.add_reaction("👍")

    @commands.group()
    @commands.check(isAdmin)
    async def admin(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.message.reply(content="/admin add | remove | list")

    @admin.command(name="add")
    async def add_admin(self, ctx: commands.Context, admin_name):
        if admin_name in admins:
            return

        with open(join("files", "settings.json")) as f:
            settings = json.load(f)
        settings["admins"].append(admin_name)
        admins.append(admin_name)

        with open(join("files", "settings.json"), "w") as f:
            json.dump(settings, f)

    @admin.command(name="delete", aliases=["remove"])
    async def delete_admin(self, ctx: commands.Context, admin_name):
        if admin_name not in admins or len(admins) == 1 or admin_name == "shayklos":
            return

        with open(join("files", "settings.json")) as f:
            settings = json.load(f)
        settings["admins"].remove(admin_name)
        admins.remove(admin_name)

        with open(join("files", "settings.json"), "w") as f:
            json.dump(settings, f)

    @admin.command(name="list", aliases=["ls"])
    async def admin_list(self, ctx):
        await ctx.send(content=" ".join([admin for admin in admins]))

    @commands.group()
    @commands.check(isAdmin)
    async def sql(self, ctx: commands.Context):
        """
        Runs a SQL script. Please know what you're doing...
        """
        if ctx.invoked_subcommand is None:
            await ctx.message.reply(content="/sql read | write")

    @sql.command()
    async def read(self, ctx: commands.Context, *, script: str):
        self.bot.db.row_factory = None
        sql = await self.bot.db.execute(script)
        result = await sql.fetchall()
        await ctx.reply(content = str(result))
        self.bot.db.row_factory = aiosqlite.Row
        await ctx.message.add_reaction("👍")

    @sql.command()
    async def write(self, ctx: commands.Context, *, script: str):
        await self.bot.db.execute(script)
        await self.bot.db.commit()
        await ctx.message.add_reaction("👍")

    @commands.command()
    @commands.check(isAdmin)
    async def get_log(self, ctx: commands.Context, log_name: str):
        max_filesize_discord = 1024*1024 * 24 # You can only send files smaller than 25 MB. We'll settle for 24

        with open(join("files", "logs", log_name + ".txt"), 'rb') as f:
            f.seek(0, 2) # Go to the end of file
            if f.tell() > max_filesize_discord:
                f.seek(-max_filesize_discord, 2) # Only send the last part of the log
            else:
                f.seek(0) # Go to the start; send the whole file

            await ctx.send(file=discord.File(f))

async def setup(bot: commands.Bot):
    await bot.add_cog(DevCommands(bot))
    print("Dev commands were loaded.")
