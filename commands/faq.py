import discord
from discord import app_commands
from discord.ext import commands
import sys, os
from os import sep
sys.path.append(f'..{sep}c2-stats-bot')
from settings import admins
from textwrap import dedent
import json

class FAQ_Commands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 
       
    # @commands.group()
    # async def faq(self, ctx: commands.Context):
    #     if ctx.invoked_subcommand is None:
    #         command = self.bot.get_command('faq help')
    #         ctx.command = command
    #         ctx.invoked_subcommand = command
    #         await self.bot.invoke(ctx)

    # @faq.command(aliases = aliases['webmaster'])
    # async def webmaster(self, ctx: commands.Context):
    #     await ctx.reply(dedent("""
    #         Simon, Cultris II developer, has stated he will update the game only after the game has a webmaster.
    #         Anyone can apply to be one, although this would be a long term job with no pay. Contact Simon via email: `de@iru.ch`"""))
            
    # @faq.command(aliases = aliases['simon'])
    # async def simon(self, ctx: commands.Context):
    #     await ctx.reply(dedent("""
    #         Cultris II only developer is Simon Felix. The only way to get in touch with Simon is via email: `de@iru.ch`"""))       
        
        
    # @faq.command(aliases = aliases['mac'])
    # async def mac(self, ctx: commands.Context):
    #     await ctx.reply(dedent("""
    #         There's no official support for macOS.
    #         However, some users have reported they were able to play using external software, check:
    #         https://discord.com/channels/202843125633384448/516686648201707548/1182624707716055040
    #         https://discord.com/channels/202843125633384448/516689168223567872/1042891393019953172"""))

    # @faq.command(aliases = aliases['patch'])
    # async def patch(self, ctx: commands.Context):
    #     await ctx.reply(dedent("""
    #         The Cultris II patch made by Def, significantly improves the game's performance.
    #         [You can download it here](https://github.com/zDEFz/c2-patch). There's a video in the description with indications in how to install the patch (it's easy!). This patch also allows disabling some ingame sounds, for additional performance gain."""))

    # @faq.command(aliases = aliases['c1soundtrack'])
    # async def c1soundtrack(self, ctx: commands.Context):
    #     await ctx.reply(dedent("""
    #         [Here's a list of the songs in Cultris I](https://docs.google.com/spreadsheets/d/1MPaLgEnlx9bNBmmwzxY0UeiotZ7LZ8VXz64qYdMU24I)."""))
        
    # @commands.group()
    # async def faq(self, ctx: commands.Context, question: str):
        
    @staticmethod
    def available_faqs(aliases_dict: dict, long = True) -> str:
        s = ""
        for name, aliases in aliases_dict.items():
            line = f"/faq {name}"
            if long : line += " | " + " | ".join(alias for alias in aliases)
            s += line + '\n'

        # Avoid reaching Discord message limit of 2000 characters. Now, you should think about separating this into different messages. Reflect on what you've done and what you've accomplished. Consider the consequences of your acts.
        if len(s) > 2000: return FAQ_Commands.available_faqs(aliases_dict, long = False)
        return s

    @commands.group(invoke_without_command = True)
    async def faq(self, ctx: commands.Context, question: str):
        with open("files/faq.json") as f: faq = json.load(f)
        
        print(ctx.invoked_subcommand)
        print(question)
        # Check if the question is directly in faqs
        if answer := faq['faqs'].get(question):
            await ctx.reply(content = answer)

        # Check if the question is one of the aliases instead
        else:
            for name, aliases in faq['aliases'].items():
                if question in aliases:
                    await ctx.reply(content = faq['faqs'][name])
                    return
                
            # Question not in FAQ, default to list of faqs
            else:
                await ctx.reply(content = FAQ_Commands.available_faqs(faq['aliases']))

    @faq.command()
    async def add(self, ctx: commands.Context, question: str, *, answer: str):
        print("question:", question, "answer", answer)
        with open("files/faq.json") as f: faq = json.load(f)
        faq['faqs'][question] = answer
        with open("files/faq.json", 'w') as f: json.dump(faq, f)

    @faq.command()
    async def delete(self, ctx: commands.Context, question):
        with open("files/faq.json") as f: faq = json.load(f)
        try: faq['faqs'].pop(question)
        except KeyError: print("No question with that name.")
        with open("files/faq.json", 'w') as f: json.dump(faq, f)


async def setup(bot: commands.Bot):
    await bot.add_cog(FAQ_Commands(bot))
    print(f"Loaded /faq command.")
