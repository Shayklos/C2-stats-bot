import discord
from discord import app_commands
from discord.ext import commands
from discord.ui.item import Item
from typing import Any
import sys, traceback
sys.path.append('../c2-stats-bot')
from logger import *
import database, methods
from CultrisView import CultrisView


"""
Displays stats of a Cultris II user in the last few days. 

The days can be choosen from 1 to a database maximum (default 30).

There stats are divided in three parts:
- General stats
    Right now, the following are displayed

        Rank - Score     Recorded Peak   Netscore
        Minutes played   Games           Winrate
        Best Combo       Avg Combo       SPM
        Blocked%         OPB             OPM
        Max BPM          BPM             
        Power            Efficiency      

- Cheese stats
    Displays top times with their corresponding BPM in the range selected

- Combo stats
    Displays combo counts in the range selected
        
"""


class StatsView(CultrisView):

    def __init__(self, bot, author, userId, days):
        super().__init__(bot=bot, author=author)
        self.command = '/stats'
        self.desktop = True

        self.userId = userId
        self.days = days
        self.state = 0 #0: stats. 1: cheese. 2: combo


    async def createStatsEmbed(self, userId, days):
            """Returns Discord embed of regular stats (Power, Efficiency, Average Combo, etc)"""

            timeStats = await database.time_based_stats(self.bot.db, userId, days=days)
            player = self.player
            netscore, netscoreDays = await database.getNetscore(self.bot.db, userId, days=days)

            #Preview of the order of the discord Embed fields
            fields = (
                ["Rank - Score",     "Recorded Peak",   "Netscore"],
                ("Minutes played",   "Games",           "Winrate"),
                ("Best Combo",       "Avg Combo",       "SPM"),
                ("Blocked%",         "OPB",             "OPM"),
                ("Max BPM",          "BPM",             ""),
                ("Power",            "Efficiency",      ""),
            )
            
            values = dict()
            if player["rank"]:
                values["Rank - Score"] = f"{player['rank']} ({player['score']:.1f})"
                values["Recorded Peak"] = f"{player['peakRank']} ({player['peakRankScore']:.1f})"

                if netscoreDays:
                    if netscoreDays == days:
                        values['Netscore'] = round(player['score'] - netscore,1)

                    #Since netscores are only saved up to 7 days, it needs to be specified when stats for more than a week are requested  
                    else:
                        values[f'Netscore ({netscoreDays}d)'] = round(player['score'] - netscore,1)
                        fields[0][2] = f'Netscore ({netscoreDays}d)'

            if timeStats["played"]:
                values["Minutes played"] = f"{timeStats['mins']:.1f}m"
                values["Games"]          = timeStats["played"]
                values["Winrate"]        = f"{timeStats['winrate']:.1f}%"
                values["Best Combo"]     = round(timeStats["bestCombo"], 1)
                values["Avg Combo"]      = round(timeStats["avgCombo"], 1)
                values["SPM"]            = round(timeStats["spm"], 1)
                values["Blocked%"]       = f"{timeStats['blocked%']:.1f}%"
                values["OPB"]            = f"{timeStats['opb']:.1f}%"
                values["OPM"]            = round(timeStats["opm"], 1)
                values["Max BPM"]        = round(timeStats["bestBPM"], 1)
                values["BPM"]            = round(timeStats["bpm"], 1)
                values["Power"]          = round(timeStats['power'], 1)
                values["Efficiency"]     = f"{timeStats['ppb']:.1f}%"
            else:
                values["Minutes played"] = "0"
            
            
            return self.embed(
                fields, values,
                embed = discord.Embed(
                    title=player["name"],
                    color=0x0B3C52,
                    url=f"https://gewaltig.net/ProfileView/{userId}",
                    description=f"{days} days stats:"
                ),
                thumbnail = f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png"
                )


    async def createCheeseEmbed(self, userId, days):
        """Returns Discord embed of Cheese Stats (Times and BPM) of top 20 times"""

        cheese = await database.userCheeseTimes(self.bot.db, userId, days)
        player = self.player
        
        embed = discord.Embed(
                title=f"Cheese times of {player['name']} ({days}d)",
                color=0xFFFF70,
            )

        if self.desktop: #Desktop view; uses embed fields to align values
            place = 1
            places = ""
            times = ""
            bpms = ""
            for time, bpm in cheese:
                places += f"{place}\n"
                times  += f"{time}\n"
                bpms   += f"{bpm}\n"
                place  += 1
           
            embed.add_field(name='Rank', value=places)
            embed.add_field(name='Time', value=times)
            embed.add_field(name='BPM',  value=bpms)
        else: #Phone view; uses only embed description since embed fields are not inlined in phone, worse readability on desktop
            description = ""
            for time, bpm in cheese:
                description += f"1. **{time}** at {bpm} BPM\n" #Markdown takes care of the counting
            
            embed.description = description

        embed.set_thumbnail(url=f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png")
        return embed


    async def createComboEmbed(self, userId, days):
        """Returns Discord embed of Combo Stats (Combo, Number of times that combo has been done, Percentage of the count over total)"""

        spread = await database.userComboSpread(self.bot.db, userId, days)
        player = self.player
        total = sum([x[1] for x in spread]) # Total games played in Standard calculated through the sum of counts of each combo
        
        embed = discord.Embed(
            title=f"Combo spread of {player['name']} ({days}d)",
            color=0xFF0000,
        )
        if self.desktop: #Desktop view; uses embed fields to align values
            combos = ""
            counts = ""
            percentages = ""
            for combo, count in spread:
                combos      += f"{combo}\n"
                counts      += f"{count}\n"
                percentages += f"{100*count/total:.1f} %\n"

            embed.add_field(name='Combo', value=combos)
            embed.add_field(name='Count', value=counts)
            embed.add_field(name='%',     value=percentages)
        else: #Phone view; uses only embed description since embed fields are not inlined in phone, worse readability on desktop
            description = ""
            for combo in spread:
                description += f"{combo[0]}: {combo[1]} ({100*combo[1]/total:.1f} %)\n"

            embed.description = description
        embed.set_thumbnail(url=f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png")
        return embed


    async def editEmbed(self, interaction: discord.Interaction):
        match self.state:
            case 0: #Stats
                embed = await self.createStatsEmbed(self.userId, self.days)
            case 1: #Cheese
                embed = await self.createCheeseEmbed(self.userId, self.days)
            case 2: #Combo spread
                embed = await self.createComboEmbed(self.userId, self.days)

        await interaction.response.edit_message(embed=embed, view=self) 

    @discord.ui.button(label="Week down", row = 0, style=discord.ButtonStyle.primary, emoji="⏬") 
    async def week_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.days = max(1, self.days-7)
        if self.days == 1:
            self.disable_buttons(["Day down", "Week down"])
        self.enable_buttons(["Day up", "Week up"])
        await self.editEmbed(interaction)


    @discord.ui.button(label="Day down", row = 0, style=discord.ButtonStyle.primary, emoji="⬇️") 
    async def day_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.days = max(1, self.days-1)
        if self.days == 1:
            self.disable_buttons(["Day down", "Week down"])
        self.enable_buttons(["Day up", "Week up"])
        await self.editEmbed(interaction)


    @discord.ui.button(label="Day up", row = 0, style=discord.ButtonStyle.primary, emoji="⬆️") 
    async def day_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.days = min(database.dbDaysLimit, self.days+1)
        if self.days == database.dbDaysLimit:
            self.disable_buttons(["Day up", "Week up"])
        self.enable_buttons(["Day down", "Week down"])
        await self.editEmbed(interaction)   


    @discord.ui.button(label="Week up", row = 0, style=discord.ButtonStyle.primary, emoji="⏫") 
    async def week_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.days = min(database.dbDaysLimit, self.days+7)
        if self.days == database.dbDaysLimit:
            self.disable_buttons(["Day up", "Week up"])
        self.enable_buttons(["Day down", "Week down"])
        await self.editEmbed(interaction)


    @discord.ui.button(label="Round stats", row=1, style = discord.ButtonStyle.primary, emoji = "📊", disabled = True) 
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.state = 0
        button.disabled = True
        self.enable_buttons(["Cheese times", "Combo spread"])

        await self.editEmbed(interaction)


    @discord.ui.button(label="Cheese times", row=1, style=discord.ButtonStyle.primary, emoji="🧀") 
    async def cheese(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.state = 1
        button.disabled = True
        self.enable_buttons(["Round stats", "Combo spread"])

        await self.editEmbed(interaction)
        

    @discord.ui.button(label="Combo spread", row=1, style = discord.ButtonStyle.primary, emoji = "🔢") 
    async def combo(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.state = 2
        button.disabled = True
        self.enable_buttons(["Round stats", "Cheese times"])

        await self.editEmbed(interaction)

    @discord.ui.button(label="Phone view", row=2, style = discord.ButtonStyle.primary, emoji = "\U0001F4BB") 
    async def phonedesktoptoggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Intended to be used to change the format of Combo and Cheese parts of this command, from a desktop view that it's
        not very readable on phone, to a phone format that is annoying to look at on desktop comparatively"""

        self.logButton(interaction,button)
        button.label = "Desktop view" if button.label == "Phone view" else "Phone view"

        button.emoji = "\U0001F4BB" if button.emoji == "\U0001f4f1" else "\U0001f4f1"
        self.desktop = False if self.desktop else True
        await self.editEmbed(interaction)



class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    @app_commands.command(description="Returns stats of a user. If you can't find the user, maybe try with an old nickname?")
    @app_commands.rename(usernameInput="username")
    @app_commands.describe(usernameInput='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
    async def stats(self, interaction: discord.Interaction, usernameInput: str= None, days: app_commands.Range[int, 1, 30] = 7):
        try:
            correct = await methods.checks(interaction)
            if not correct:
                return
            
            if not usernameInput:
                usernameInput = interaction.user.display_name

            ratio, userId, username = await database.fuzzysearch(self.bot.db, usernameInput.lower())
            msg = None if ratio == 100 else f"No user found with name \'{usernameInput}\'. Did you mean \'{username}\'?"

            view = StatsView(self.bot, interaction.user, userId, days)
            view.player = await database.player_stats(self.bot.db, userId)

            embed = await view.createStatsEmbed(userId, days)
            await interaction.response.send_message(msg, embed=embed, view=view)
            view.message = await interaction.original_response()
            

        except Exception as e:
            print(e)
            log(traceback.format_exc())




async def setup(bot: commands.Bot):
    await bot.add_cog(Stats(bot))
    print(f"Loaded /stats command.")