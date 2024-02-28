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
    async def faq(self, ctx: commands.Context, question: str):
        with open("files/faq.json") as f: faq = json.load(f)
        
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

    @faq.group()
    async def add(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(content="/faq add question [question] [answer]\n /faq add alias [question] [new_alias] [new_alias] ... [new_alias]")

    @add.command(name="question")
    async def add_question(self, ctx: commands.Context, question: str, *, answer: str):
        with open("files/faq.json") as f: faq = json.load(f)
        faq['faqs'][question] = answer
        faq['aliases'][question] = []
        with open("files/faq.json", 'w') as f: json.dump(faq, f)

    @add.command(name="alias", aliases = ["aliases"])
    async def add_alias(self, ctx: commands.Context, question: str, *, new_aliases: str):
        with open("files/faq.json") as f: faq = json.load(f)
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
        with open("files/faq.json", 'w') as f: json.dump(faq, f)

    @faq.group(aliases = ["remove"])
    async def delete(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply(content="/faq delete question [question] [answer]\n /faq delete alias [question] [alias_to_remove] [alias_to_remove] ... [alias_to_remove]")
        
    @delete.command(name="question")
    async def delete_question(self, ctx: commands.Context, question: str):
        with open("files/faq.json") as f: faq = json.load(f)
        try: 
            faq['faqs'].pop(question)
            faq['aliases'].pop(question)
            
        except KeyError: await ctx.reply(content="No question with that name.")
        with open("files/faq.json", 'w') as f: json.dump(faq, f)

    @delete.command(name="alias", aliases = ["aliases"])
    async def delete_alias(self, ctx: commands.Context, question: str, *, alias_to_remove: str):
        with open("files/faq.json") as f: faq = json.load(f)
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
        with open("files/faq.json", 'w') as f: json.dump(faq, f)


async def setup(bot: commands.Bot):
    await bot.add_cog(FAQ_Commands(bot))
    print(f"Loaded /faq command.")
