import aiosqlite
import discord
from discord.ext import commands
from discord.ui import Button, View
import sys
import os
from os import sep
from os.path import join
import json
from importlib import reload

sys.path.append(f"..{sep}c2-stats-bot")
import settings as SETTINGS
from bot import GUILD_ID


class DevCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    def isAdmin(ctx: commands.Context):
        print(f"/{ctx.command} was called by {ctx.author.name}")
        return ctx.author.name in SETTINGS.admins

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.reply("You do not have the required permissions to use this command.")

    @commands.command()
    @commands.check(isAdmin)
    async def ping(self, ctx: commands.Context):
        await ctx.send(
            f"Average websocket latency: {round(self.bot.latency * 1000, 2)}ms"
        )

    @commands.command(name='reload', aliases=["r", "rl"])
    @commands.check(isAdmin)
    async def reload_command(self, ctx: commands.Context, command: str = "all"):
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
    # @commands.check(isAdmin)
    @commands.cooldown(1, 300, commands.BucketType.default) # 1 use per 5 min max
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

    @reload_event.error
    async def reload_event_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            if DevCommands.isAdmin(ctx):  # Bypass the cooldown for admins
                await ctx.reinvoke()  # Reinvoke the command without the cooldown
            else:
                await ctx.send(f"This command is on cooldown. Try again after {round(error.retry_after, 2)} seconds.")
        
        else:
            raise error


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
#---------------------------------------------------------ADMIN
    # Kinda useless now that /settings command exists
    @commands.group()
    @commands.check(isAdmin)
    async def admin(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.message.reply(content="/admin add | remove | list")

    @admin.command(name="add")
    async def add_admin(self, ctx: commands.Context, admin_name):
        if admin_name in SETTINGS.admins:
            return

        with open(join("files", "settings.json")) as f:
            settings = json.load(f)
        settings["admins"].append(admin_name)
        SETTINGS.admins.append(admin_name)

        with open(join("files", "settings.json"), "w") as f:
            json.dump(settings, f)

    @admin.command(name="delete", aliases=["remove"])
    async def delete_admin(self, ctx: commands.Context, admin_name):
        if admin_name not in SETTINGS.admins or len(settings.admins) == 1 or admin_name == "shayklos":
            return

        with open(join("files", "settings.json")) as f:
            settings = json.load(f)
        settings["admins"].remove(admin_name)
        SETTINGS.admins.remove(admin_name)

        with open(join("files", "settings.json"), "w") as f:
            json.dump(settings, f)

    @admin.command(name="list", aliases=["ls"])
    async def admin_list(self, ctx):
        reload(SETTINGS)
        await ctx.send(content=" ".join([admin for admin in SETTINGS.admins]))
#---------------------------------------------------------SQL
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
        max_filesize_discord = round(1024*1024 * 9.8) # You can only send files smaller than 10 MB. We'll settle for 9.8

        with open(join("files", "logs", log_name + ".txt"), 'rb') as f:
            f.seek(0, 2) # Go to the end of file
            if f.tell() > max_filesize_discord:
                f.seek(-max_filesize_discord, 2) # Only send the last part of the log
            else:
                f.seek(0) # Go to the start; send the whole file

            await ctx.send(file=discord.File(f))

    @commands.command()
    @commands.check(isAdmin)
    async def swap(self, ctx: commands.Context, where):
        att = ctx.message.attachments[0]
        with open(where, 'wb') as f:
            await att.save(f)
                        
        await ctx.message.add_reaction("👍")
#---------------------------------------------------------SETTINGS
    @commands.group(invoke_without_command = True)
    @commands.check(isAdmin)
    async def settings(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(content="/settings see | modify | reload")

    @settings.command(aliases = ['check'])
    async def see(self, ctx: commands.Context, setting: str = None):
        if not setting:
            await ctx.reply(content="/settings see <setting>")
            return 
        
        with open(join("files", "settings.json")) as f: data = json.load(f)

        await ctx.reply(content=f"{setting}: {data.get(setting)}")
        await ctx.message.add_reaction("👍")


    @settings.command()
    async def modify(self, ctx: commands.Context, setting: str = None, *, new_setting: str):
        if not setting:
            await ctx.reply(content="/settings modify <setting>")
            return 
        
        # Verify setting exists
        with open(join("files", "settings.json")) as f: data = json.load(f)
        old = data.get(setting)
        if old is None:
            await ctx.reply(content=f"Setting {setting} not found")
            return
        
        # Parse new setting
        if isinstance(old, list):
            if new_setting[0] != '[' or new_setting[-1] != ']':
                await ctx.reply(content=f"Setting {setting} should be in a Python list format")
                return

            elements = new_setting[1:-1].split(', ') #notice its comma space
            if '"' in elements[0]: #Contents are strings
                new = [e.replace('"', '') for e in elements]
            elif "." in elements[0]: #Contents are floats
                new = [float(e) for e in elements]
            else: #Contents are integers
                new = [int(e) for e in elements]
        
        elif isinstance(old, int) or isinstance(old, float) or isinstance(old, str) or isinstance(old, bool):
            new = type(old)(new_setting)
        
        else:
            await ctx.reply(content="Modifying this setting not supported through commands")
            return
        
        # Create a Confirm/Cancel UI
        confirm_button = Button(label="Confirm", style=discord.ButtonStyle.green)
        cancel_button = Button(label="Cancel", style=discord.ButtonStyle.red)
        
        # Define button behavior
        async def confirm_callback(interaction: discord.Interaction):
            # Update settings.json, reload settings module
            data[setting] = new
            with open(join("files", "settings.json"), 'w') as f:
                json.dump(data, f)
            reload(SETTINGS)
            await interaction.response.edit_message(content="Setting updated successfully.", view=None)

        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="Operation cancelled.", view=None)

        confirm_button.callback = confirm_callback
        cancel_button.callback = cancel_callback

        view = View()
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        # Send the confirmation message with buttons
        await ctx.reply(content=f"Are you sure you want to update `{setting}` \n\nfrom \n`{str(old)}` \nto \n`{str(new)}`?", view=view)
        await ctx.message.add_reaction("👍")

    @settings.command(name='reload')
    async def reload_settings(self, ctx: commands.Context, setting: str = None):
        reload(SETTINGS)
        await ctx.reply(content="Settings reloaded.")
        await ctx.message.add_reaction("👍")



async def setup(bot: commands.Bot):
    await bot.add_cog(DevCommands(bot))
    print("Dev commands were loaded.")
