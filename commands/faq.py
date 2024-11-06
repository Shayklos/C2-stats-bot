import discord
from discord import app_commands
from discord.ext import commands
import sys
from os.path import join
from os import sep
sys.path.append(f'..{sep}c2-stats-bot')
from settings import admins
from textwrap import dedent
import json

class FAQ_Commands(commands.Cog):
    """
    Cog that manages all related to the /faq command. 

    Usage:
    /faq [question]
        will make the bot send an answer to [question]. The anser to this question is stored in files/faq.json. 
        Different values of [question] will grant the same reply, these are managed in the `aliases` in files/faq.json. 

    /faq add question [name] [answer]
        will add a question named [name] with the answer [answer]

    /faq delete question [name]
        will delete the question named [name]. /faq remove question [name] also works. 

    /faq add alias [question] [aliases]
        will add aliases [aliases] to question [question]. The aliases, if more than one, should be separated by spaces. /faq add aliases [question] [aliases] also works.

    /faq delete alias [question] [aliases]
        will remove aliases [aliases] from question [question]. The aliases, if more than one, should be separated by spaces. /faq remove aliases [question] [aliases] also works.    


    TODO:
        -/faq edit question [question] [answer] to edit a question
        -/faq edit alias|aliases [question] [aliases] to edit a question's aliases
        -/faq aliases [question] to show aliases related to a specific question
        -/faq delete alias should be able to delete the main question name, if there is an alias for that question
        -/faq delete question should work with aliases without the need to input main question name
    """
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot 

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.reply("You do not have the required permissions to use this command.")

    @staticmethod
    def available_faqs(aliases_dict: dict, long = True) -> str:
        s = ""
        for name, aliases in aliases_dict.items():
            line = f"/faq {name}"
            if long and aliases : line += " | " + " | ".join(alias for alias in aliases)
            s += line + '\n'

        # Avoid reaching Discord message limit of 2000 characters. Now, you should think about separating this into different messages. Reflect on what you've done and what you've accomplished. Consider the consequences of your acts.
        if len(s) > 2000: return FAQ_Commands.available_faqs(aliases_dict, long = False)
        return s

    @commands.group(invoke_without_command = True)
    async def faq(self, ctx: commands.Context, question: str = None):
        with open(join("files", "faq.json")) as f: faq = json.load(f)
        
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

    @commands.check(lambda ctx : ctx.author.name in admins)
    @faq.group()
    async def add(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(content="/faq add question [question] [answer]\n /faq add alias [question] [new_alias] [new_alias] ... [new_alias]")

    @add.command(name="question")
    async def add_question(self, ctx: commands.Context, question: str, *, answer: str):
        if question in ['add', 'remove', 'delete']:
            await ctx.reply(content='This would cause conflicts.')
            return
        with open(join("files", "faq.json")) as f: faq = json.load(f)
        faq['faqs'][question] = answer
        faq['aliases'][question] = []
        with open(join("files", "faq.json"), 'w') as f: json.dump(faq, f)

    @add.command(name="alias", aliases = ["aliases"])
    async def add_alias(self, ctx: commands.Context, question: str, *, new_aliases: str):
        with open(join("files", "faq.json")) as f: faq = json.load(f)
        if faq['aliases'].get(question) is not None: 
            for alias in new_aliases.split(): faq['aliases'][question].append(alias.lower())
        else:
            for name, aliases in faq['aliases'].items():
                if question in aliases:
                    for alias in new_aliases.split(): 
                        faq['aliases'][name].append(alias.lower())
                    break
            else:
                await ctx.reply(content = "No question with that name.")
        with open(join("files", "faq.json"), 'w') as f: json.dump(faq, f)

    @commands.check(lambda ctx : ctx.author.name in admins)
    @faq.group(aliases = ["remove"])
    async def delete(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(content="/faq delete question [question]\n /faq delete alias [question] [alias_to_remove] [alias_to_remove] ... [alias_to_remove]")
        
    @delete.command(name="question")
    async def delete_question(self, ctx: commands.Context, question: str):
        with open(join("files", "faq.json")) as f: faq = json.load(f)
        try: 
            faq['faqs'].pop(question)
            faq['aliases'].pop(question)
            
        except KeyError: await ctx.reply(content="No question with that name.")
        with open(join("files", "faq.json"), 'w') as f: json.dump(faq, f)

    @delete.command(name="alias", aliases = ["aliases"])
    async def delete_alias(self, ctx: commands.Context, question: str, *, alias_to_remove: str):
        with open(join("files", "faq.json")) as f: faq = json.load(f)
        if faq['aliases'].get(question) is not None: 
            for alias in alias_to_remove.split(): faq['aliases'][question].remove(alias)
        else:
            for name, aliases in faq['aliases'].items():
                if question in aliases:
                    for alias in alias_to_remove.split(): 
                        faq['aliases'][name].remove(alias)
                    break
            else:
                await ctx.reply(content = "No question with that name.")
        with open(join("files", "faq.json"), 'w') as f: json.dump(faq, f)

    @commands.check(lambda ctx : ctx.author.name in admins)
    @commands.command()
    async def export_faq(self, ctx: commands.Context):
        await ctx.send(file=discord.File(join("files", "faq.json")))
        

async def setup(bot: commands.Bot):
    await bot.add_cog(FAQ_Commands(bot))
    print(f"Loaded /faq command.")
