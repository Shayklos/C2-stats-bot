from typing import Any
import discord
from discord.interactions import Interaction
from discord.ui.item import Item
from logger import *
from settings import botTimeout
from os.path import join

"""Default View class used with this bot."""

class CultrisView(discord.ui.View):
    def __init__(self, bot, author):
        super().__init__(timeout=botTimeout)
        self.bot = bot 
        self.interactionUser = author

    async def on_timeout(self):
        for item in self.children:
            item.style = discord.ButtonStyle.grey
            item.disabled = True
        await self.message.edit(view=self)

    
    async def interaction_check(self, interaction: discord.Interaction):
        #checks if user who used the button is the same who called the command
        if interaction.user == self.interactionUser:
            return True
        else:
            await interaction.user.send("Only the user who called the command can use the buttons.")
    

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: Item[Any]) -> None:
        print(error)
        await interaction.user.send("Something went horribly wrong. Uh oh. Please report it to `shayklos` on Discord!")
    

    def enable_buttons(self, list):
        for item in self.children:
            if item.label in list:
                item.disabled = False


    def disable_buttons(self, list):
        for item in self.children:
            if item.label in list:
                item.disabled = True


    def logButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        log(f"{interaction.user.display_name} ({interaction.user.name}) in {self.command} pressed [{button.label}]",join("files","log_discord.txt"))

    
    def embed(self, list, values, title = None, thumbnail = None, embed: discord.Embed = None):
        """
        Utility function for making discord embeds while previewing the position of its fields on `list`
        """
        if not embed:
            embed = discord.Embed(
                title = title,
                color = 0x0B3C52,
            )

        for line in list:
            for element in line:
                if element == "":
                    embed.add_field(name = "", value = "")
                    continue

                if values.get(element) is None:
                    continue

                embed.add_field(name = element, value = values[element])

        if thumbnail:
            embed.set_thumbnail(url = thumbnail)

        return embed