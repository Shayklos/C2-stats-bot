import discord, urllib.request, json
from discord import app_commands
from discord.ext import commands
from discord.ui.item import Item
from typing import Any
import sys, traceback
sys.path.append('../c2-stats-bot')
from logger import *
from CultrisView import CultrisView
import database, methods


CHALLENGES = ['Maserati', 'Survivor', 'Swiss cheese', '49.6 µFortnight', 'Ten', "James Clewett's", 'Quickstart', 'Shi Tai Ye']

class ChallengeButton(discord.ui.Button):
    async def callback(self, interaction):
        self.view: ChallengesView

        self.view.challenge = self.label
        log(f"{self.view.interactionUser.display_name} ({self.view.interactionUser.name}) on {self.view.command} pressed button {self.label}", "files/log_discord.txt")
        await interaction.response.edit_message(embed = self.view.createEmbed(interaction), view = self.view)


class ChallengesView(CultrisView):

    def __init__(self, bot, author: discord.User, userId: int, challenge: str):
        super().__init__(bot=bot, author=author)
        self.command = '/challenges'

        self.interactionUser = author
        self.userId = userId
        self.challenge = challenge

        with urllib.request.urlopen(database.BASE_USER_URL+str(userId)) as URL:
            self.playerData = json.load(URL)
        for i, label in enumerate(CHALLENGES):
            self.add_item(
                ChallengeButton(label = label, 
                                row = i//4, #Half of the buttons will be on the first row, the other half will be on the second row
                                style=discord.ButtonStyle.primary))


    def createEmbed(self, interaction: discord.Interaction):
        embed = discord.Embed(
                    title=f"{self.challenge} of {self.playerData.get('name')}",
                    color=0x0B3C52,
                    url=f"https://gewaltig.net/ProfileView/{self.userId}",
                )

        challenge = self.playerData.get("challenges")
        match self.challenge:
            case "Maserati":
                data = challenge.get("ol-maserati")
                embed.add_field(name = "Time", value = f"{round(data.get('playDuration'), 2)}s")
                embed.add_field(name = "Blocks", value = data.get("blocks"))

            case "Survivor":
                data = challenge.get("ol-survivor")
                embed.add_field(name = "Time", value = f"{data.get('playDuration') // 60 :.0f}m {data.get('playDuration')%60:.2f}s")
                embed.add_field(name = "BPM", value = f"{60*data.get('blocks')//data.get('playDuration'):.0f}")

            case "Swiss cheese":
                data = challenge.get("ol-cheese")
                embed.add_field(name = "Time", value = f"{round(data.get('playDuration'), 2)}s")
                embed.add_field(name = "Blocks", value = data.get("blocks"))

            case "49.6 µFortnight":
                data = challenge.get("ol-send")
                embed.add_field(name = "Lines sent", value = data.get("linesSent"))
                embed.add_field(name = "Sent per block", value = f"{data.get('linesSent')/data.get('blocks'):.2f}")
                embed.add_field(name = "BPM", value = f"{60*data.get('blocks')//data.get('playDuration'):.0f}")

            case "Ten":
                data = challenge.get("ol-ten")
                embed.add_field(name = "Time", value = f"{round(data.get('playDuration'), 2)}s")
                embed.add_field(name = "BPM", value = f"{60*data.get('blocks')//data.get('playDuration'):.0f}")

            case "James Clewett's":
                data = challenge.get("ol-clewett")
                embed.add_field(name = "Tetrises", value = data.get("tetrii"))
                embed.add_field(name = "Time", value = f"{data.get('playDuration') // 60 :.0f}m {data.get('playDuration')%60:.2f}s")

            case "Quickstart":
                data = challenge.get("ol-qs")
                embed.add_field(name = "Time", value = f"{round(data.get('playDuration'), 2)}s")
                embed.add_field(name = "BPM", value = f"{60*data.get('blocks')//data.get('playDuration'):.0f}")

            case "Shi Tai Ye":
                data = challenge.get("ol-tgm")
                embed.add_field(name = "Lines cleared", value = data.get("linesCleared"))
                embed.add_field(name = "Time", value = f"{data.get('playDuration') // 60 :.0f}m {data.get('playDuration')%60:.2f}s")

        embed.description = f"PB obtained on {data.get('date')}"
        embed.set_thumbnail(url=f"https://www.gravatar.com/avatar/{self.playerData.get('gravatarHash')}?d=https://i.imgur.com/Gms07El.png")

        
        return embed


class Challenges(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot 
    

    @app_commands.command(description="Returns stats of the singleplayer challenges.")
    @app_commands.describe(challenge='By default Maserati (40L Sprint).')
    async def challenges(self, interaction: discord.Interaction, username: str = None, challenge: str = 'Maserati'):
        try:
            correct = await methods.checks(interaction)
            if not correct:
                return
            
            if not username:
                username = interaction.user.display_name

            ratio, userId, user = await database.fuzzysearch(self.bot.db, username.lower())
            msg = None if ratio == 100 else f"No user found with name \'{username}\'. Did you mean \'{user}\'?"
    
            view = ChallengesView(self.bot, interaction.user, userId, challenge)

            await interaction.response.send_message(embed = view.createEmbed(challenge), view=view)
            view.message = await interaction.original_response()
            

        except Exception as e:
            print(e)
            log(traceback.format_exc())


    @challenges.autocomplete('challenge')
    async def challenges_autocomplete(self, interaction: discord.Interaction, current: str):      
        return [
            app_commands.Choice(name=challenge, value=challenge)
            for challenge in CHALLENGES if current.lower() in challenge.lower()
        ]
    

async def setup(bot: commands.Bot):
    await bot.add_cog(Challenges(bot))
    print(f"Loaded /challenges command.")