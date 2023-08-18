import asyncio
import os
from typing import Any
import discord
from discord import app_commands
from discord.interactions import Interaction
from discord.ui.item import Item
from dotenv import load_dotenv
import database, sqlite3
import methods
from logger import *
import traceback 

developerMode = False
if __name__ == "__main__":
    print("developerMode: ", developerMode)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')


intents = discord.Intents.all()
client  = discord.Client(intents=intents, activity=discord.Game(name="Cultris II"))
tree    = app_commands.CommandTree(client)
guild   = discord.Object(id=GUILD_ID) if developerMode else None
db = sqlite3.connect(r"files/cultris.db")








class Stats(discord.ui.View):

    def __init__(self, author, userId, days):
        super().__init__(timeout=120)
        self.interactionUser = author
        self.userId = userId
        self.days = days
        self.player = database.player_stats(db, userId)
        self.state = 0 #0: stats. 1: cheese. 2: combo
        self.command = '/stats'

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
        await interaction.user.send("Something went horribly wrong. Uh oh.")
    

    def disable_buttons(self, list):
        for item in self.children:
            if item.label in list:
                item.disabled = False


    def logButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        log(f"{interaction.user.display_name} ({interaction.user.name}) in {self.command} pressed [{button.label}]","files/log_discord.txt")


    def createStatsEmbed(self, userId, days):
            timeStats = database.time_based_stats(db, userId, days=days)
            player = self.player
            netscore, netscoreDays = database.getNetscore(db, userId, days=days)
            embed = discord.Embed(
                    title=player["name"],
                    color=0x0B3C52,
                    url=f"https://gewaltig.net/ProfileView/{userId}",
                    description=f"{days} days stats:"
                )
            if player["rank"]:
                embed.add_field(name="Rank", value=player["rank"], inline=True)
                embed.add_field(name="Score", value=f"{player['score']:.1f}", inline=True)
                embed.add_field(name="Recorded Peak", value=f"{player['peakRank']} ({player['peakRankScore']:.1f})", inline=True)
            if timeStats["played"]:
                embed.add_field(name="Minutes played", value=f"{timeStats['mins']:.1f}m", inline=True)
                embed.add_field(name="Games", value=timeStats["played"], inline=True)
                embed.add_field(name="Winrate", value=f"{timeStats['winrate']:.1f}%", inline=True)

                embed.add_field(name="Best Combo", value=round(timeStats["bestCombo"], 1), inline=True)
                embed.add_field(name="Avg Combo", value=round(timeStats["avgCombo"], 1), inline=True)
                embed.add_field(name="Avg SPM", value=round(timeStats["avgSPM"], 1), inline=True)

                embed.add_field(name="Blocked%", value=f"{timeStats['blockedpercent']:.1f}%", inline=True)
                embed.add_field(name="Avg OPB", value=f"{timeStats['outputperpiece']:.1f}%", inline=True)
                embed.add_field(name="Avg OPM", value=round(timeStats["outputperminute"], 1), inline=True)

                embed.add_field(name="Max BPM", value=round(timeStats["bestBPM"], 1), inline=True)
                embed.add_field(name="Avg BPM", value=round(timeStats["avgBPM"], 1), inline=True)

                if netscoreDays:
                    if netscoreDays == days:
                        embed.add_field(name = 'Netscore', value = round(player['score'] - netscore,1))
                    else:
                        embed.add_field(name = f'Netscore ({netscoreDays}d)', value = round(player['score'] - netscore,1))
            
            else:
                embed.add_field(name="Minutes played", value="0", inline=True)
            
            embed.set_thumbnail(url=f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png")
            return embed


    def createCheeseEmbed(self, userId, days):
        cheese = database.userCheeseTimes(db, userId, days)
        player = self.player
        place = 1
        places = ""
        times = ""
        bpms = ""
        for time, bpm in cheese:
            places += f"{str(place)}\n"
            times += f"{str(time)}\n"
            bpms += f"{str(bpm)}\n"
            place += 1

        embed = discord.Embed(
            title=f"Cheese times of {player['name']} ({days}d)",
            color=0xFFFF70,
        )
        embed.add_field(name='Rank', value=places)
        embed.add_field(name='Time', value=times)
        embed.add_field(name='BPM', value=bpms)
        embed.set_thumbnail(url=f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png")
        return embed
            

    def createComboEmbed(self, userId, days):
        spread = database.userComboSpread(db, userId, days)
        player = self.player
        combos = ""
        counts = ""
        for combo, count in spread:
            combos += f"{str(combo)}\n"
            counts += f"{str(count)}\n"

        embed = discord.Embed(
            title=f"Combo spread of {player['name']} ({days}d)",
            color=0xFF0000,
        )
        embed.add_field(name='Combo', value=combos)
        embed.add_field(name='Count', value=counts)
        embed.set_thumbnail(url=f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png")
        return embed


    async def editEmbed(self, interaction: discord.Interaction):
        match self.state:
            case 0: #Stats
                await interaction.response.edit_message(
                    embed=self.createStatsEmbed(self.userId, self.days), 
                    view=self)
            case 1: #Cheese
                await interaction.response.edit_message(
                    embed=self.createCheeseEmbed(self.userId, self.days), 
                    view=self)
            case 2: #Combo spread
                await interaction.response.edit_message(
                    embed=self.createComboEmbed(self.userId, self.days),
                    view=self) 

    @discord.ui.button(label="Week down", row = 0, style=discord.ButtonStyle.primary, emoji="⏬") 
    async def week_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.days = max(1, self.days-7)
        await self.editEmbed(interaction)


    @discord.ui.button(label="Day down", row = 0, style=discord.ButtonStyle.primary, emoji="⬇️") 
    async def day_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.days = max(1, self.days-1)
        await self.editEmbed(interaction)


    @discord.ui.button(label="Day up", row = 0, style=discord.ButtonStyle.primary, emoji="⬆️") 
    async def day_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.days = min(database.dbDaysLimit, self.days+1)
        await self.editEmbed(interaction)   


    @discord.ui.button(label="Week up", row = 0, style=discord.ButtonStyle.primary, emoji="⏫") 
    async def week_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.days = min(database.dbDaysLimit, self.days+7)
        await self.editEmbed(interaction)


    @discord.ui.button(label="Round stats", row=1, style = discord.ButtonStyle.primary, emoji = "📊", disabled = True) 
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.state = 0
        button.disabled = True
        self.disable_buttons(["Cheese times", "Combo spread"])

        await self.editEmbed(interaction)


    @discord.ui.button(label="Cheese times", row=1, style=discord.ButtonStyle.primary, emoji="🧀") 
    async def cheese(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.state = 1
        button.disabled = True
        self.disable_buttons(["Round stats", "Combo spread"])

        await self.editEmbed(interaction)
        

    @discord.ui.button(label="Combo spread", row=1, style = discord.ButtonStyle.primary, emoji = "🔢") 
    async def combo(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.state = 2
        button.disabled = True
        self.disable_buttons(["Round stats", "Cheese times"])

        await self.editEmbed(interaction)



@tree.command(description="Returns stats of a user. If you can't find the user, maybe try with an old nickname?"
              ,guild=guild
              )
@app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
async def stats(interaction: discord.Interaction, username: str=None, days: app_commands.Range[int, 1, 30] = 7):
    try:
        correct = await methods.checks(interaction)
        if not correct:
            return
        
        if not username:
            username = interaction.user.display_name

        ratio, userId, user = database.fuzzysearch(db, username.lower())
        msg = None if ratio == 100 else f"No user found with name \'{username}\'. Did you mean \'{user}\'?"
  
        view = Stats(interaction.user, userId, days)

        embed = view.createStatsEmbed(userId, days)
        await interaction.response.send_message(msg, embed=embed, view=view)
        view.message = await interaction.original_response()
        

    except Exception as e:
        print(e)
        log(traceback.format_exc())


@tree.command(description="Returns all-time stats of a user. If you can't find the user, maybe try with an old nickname?"
              ,guild=guild
              )
@app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
async def legacystats(interaction: discord.Interaction, username: str=None):
    correct = await methods.checks(interaction)
    if not correct:
        return
    
    if not username:
        username = interaction.user.display_name
    ratio, userId, user = database.fuzzysearch(db, username) #ej (80, 5840, Shay)

    msg = None
    if ratio != 100:
        msg = f"No user found with name \'{username}\'. Did you mean \'{user}\'?"
        
    
    
    player = database.player_stats(db, userId)
    # print(player)
    # print(timeStats)
    embed = discord.Embed(
            title=player["name"],
            color=0x0B3C52,
            url=f"https://gewaltig.net/ProfileView/{player['userId']}",
        )
    if player["rank"]:
        embed.add_field(name="Rank", value=player["rank"], inline=True)
        embed.add_field(name="Score", value=f"{player['score']:.1f}", inline=True)
        embed.add_field(name="Recorded Peak", value=f"{player['peakRank']} ({player['peakRankScore']:.1f})", inline=True)

    if player["playedRounds"]:
        embed.add_field(name="Best Combo", value=player["maxCombo"], inline=True)
        embed.add_field(name="Wins", value=methods.thousandsSeparator(player["wins"]), inline=True)
        embed.add_field(name="Games", value=f"{methods.thousandsSeparator(player['playedRounds'])} ({methods.thousandsSeparator(player['playedRoundsStandard'])} in Standard)", inline=True)

        embed.add_field(name="Max BPM", value=round(player["maxBPM"], 1), inline=True)
        embed.add_field(name="Avg BPM", value=round(player["avgBPM"], 1), inline=True)
        embed.add_field(name="Total Hours", value=f"{player['playedMin']/60:.1f}h", inline=True)

        embed.add_field(name="Standard time", value=f"{player['standardTime']/3600:.1f}h", inline=True)
        embed.add_field(name="Cheese time", value=f"{player['cheeseTime']/3600:.1f}h", inline=True)
        embed.add_field(name="Teams time", value=f"{player['teamsTime']/3600:.1f}h", inline=True)

        embed.add_field(name="Received lines", value=methods.thousandsSeparator(player["linesGot"]), inline=True)
        embed.add_field(name="Sent lines", value=methods.thousandsSeparator(player["linesSent"]), inline=True)
        embed.add_field(name="Blocked lines", value=methods.thousandsSeparator(player["linesBlocked"]), inline=True)

        embed.add_field(name="Sum of Max Combos", value=methods.thousandsSeparator(player["comboSum"]), inline=True)
        if player["maxCombo"] == 14:
            embed.add_field(name="14s", value=player["14s"], inline=True)
            embed.add_field(name="13s", value=player["13s"], inline=True)
        elif player["maxCombo"] == 13:
            embed.add_field(name="13s", value=player["13s"], inline=True)
            embed.add_field(name="12s", value=player["12s"], inline=True)
        elif player["maxCombo"] == 12:
            embed.add_field(name="12s", value=player["12s"], inline=True)
            embed.add_field(name="11s", value=player["11s"], inline=True)
        else:
            embed.add_field(name="11s", value=player["11s"], inline=True)
            embed.add_field(name="10s", value=player["10s"], inline=True)
        


    else:
        embed.add_field(name="Games", value=0, inline=True)
        
    
    embed.set_thumbnail(url=f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png")
    await interaction.response.send_message(msg, embed=embed)



@tree.command(description="Top 5 in SPM and Cheese times in the last 7 days.",
        guild=guild,
        )
async def weeklybest(interaction: discord.Interaction):
    correct = await methods.checks(interaction)
    if not correct:
        return
    top5SPM, top5Cheese = database.weekly_best(db)
    embed = discord.Embed(
            title="Weekly Best",
            color=0x0B3C52,
        )
    embed.add_field(name = "Top 5 SPM (7d)", value = 
                    f"""**{top5SPM[0][0]}** - {round(top5SPM[0][1])}
**{top5SPM[1][0]}** - {round(top5SPM[1][1])}
**{top5SPM[2][0]}** - {round(top5SPM[2][1])}
**{top5SPM[3][0]}** - {round(top5SPM[3][1])}
**{top5SPM[4][0]}** - {round(top5SPM[4][1])}

""", inline=True)
    embed.add_field(name = '\u2800', value = "\u2800\n\u2800\n\u2800\n\u2800\n\u2800")

    embed.add_field(name = "Top 5 Cheese times (7d)", value = 
                    f"""**{top5Cheese[0][0]}** - {round(top5Cheese[0][1],2)}
**{top5Cheese[1][0]}** - {round(top5Cheese[1][1],2)}
**{top5Cheese[2][0]}** - {round(top5Cheese[2][1],2)}
**{top5Cheese[3][0]}** - {round(top5Cheese[3][1],2)}
**{top5Cheese[4][0]}** - {round(top5Cheese[4][1],2)}

""", inline=True)
    await interaction.response.send_message(embed=embed)



@tree.command(description="Shows which users are online right now."
              ,guild=guild
              )
async def online(interaction: discord.Interaction):
    correct = await methods.checks(interaction)
    if not correct:
        return
    players = database.getPlayersOnline(db)
    msg = ""
    string = ""
    for player in players:
        string += player + ", "

    embed = discord.Embed(
            color=0x0B3C52,
            description=string[:-2],
            title="Players online"
        )
    
    if not interaction.guild and (developerMode or interaction.user.name in database.admins):        
        extradata = database.getPlayersWhoPlayedRecently(db)
        msg = "Players who played in the last hour: "
        for player in extradata.get('players'):
            msg += f"**{player[0]}**, "
        msg = msg[:-2]
        msg += "\nGuests who played in the last hour: "
        for guest in extradata.get('guests'):
            msg += f"**{guest[0]}**, "

    await interaction.response.send_message(msg[:-2], embed=embed)




# async def hello(interaction: discord.Interaction, message: discord.User):
#     await interaction.response.send_message(f"Hey {message.author.mention}!")

# hello_context_menu = app_commands.ContextMenu(
#     name='Say Hello',
#     callback=hello,
# )
# tree.add_command(hello_context_menu)


class Rankings(discord.ui.View):

    def __init__(self, author, page):
        super().__init__(timeout=120)
        self.interactionUser = author
        self.page = page
        self.command = '/rankings'

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
        await interaction.user.send("Something went horribly wrong. Uh oh.")
    

    def disable_buttons(self, list):
        for item in self.children:
            if item.label in list:
                item.disabled = False


    def logButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        log(f"{interaction.user.display_name} ({interaction.user.name}) in {self.command} pressed [{button.label}]","files/log_discord.txt")



    def createEmbed(self, page):
        pageSize = 20 
        start = pageSize * (page - 1) + 1
        end = start + pageSize -1
        data = database.getRankings(db, start, end)
        description = ""
        for element in data:
            description += f"{start}. [{element[1]}](https://gewaltig.net/ProfileView/{element[0]}) {element[2]}\n"
            start+=1

        embed = discord.Embed(
                color=0x0B3C52,
                description=description,
                title=f"Leaderboard"
            )
        return embed


    @discord.ui.button(label="Page down", row = 0, style=discord.ButtonStyle.primary, emoji="⏬") 
    async def page_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.page = max(1, self.page-1)
        embed = self.createEmbed(self.page)
        await interaction.response.edit_message(embed=embed, view = self)



    @discord.ui.button(label="Page up", row = 0, style=discord.ButtonStyle.primary, emoji="⏫") 
    async def page_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction,button)
        self.page +=1
        embed = self.createEmbed(self.page)
        await interaction.response.edit_message(embed=embed, view = self)







@tree.command(description="Displays current leaderboard. Doesn't work too well... the positions of may not be accurate.")
@app_commands.describe(page = "The page you want to see (by default 1). Negative page numbers are not allowed here.")

async def rankings(interaction: discord.Interaction, page: app_commands.Range[int, 1] = 1):
    correct = await methods.checks(interaction)
    if not correct:
        return
    
    view = Rankings(interaction.user, page)

    embed = view.createEmbed(page)
    await interaction.response.send_message(embed = embed, view = view)
    view.message = await interaction.original_response()


class Leaderboard(discord.ui.View):

    def __init__(self, author, stat, days, page):
        super().__init__(timeout=120)
        self.interactionUser = author
        self._stat = stat
        self.page = page
        self.days = days
        self.command = '/leaderboard'

    async def on_timeout(self):
        print("timeout")
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
        await interaction.user.send("Something went horribly wrong. Uh oh.")


    def logButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        log(f"{interaction.user.display_name} ({interaction.user.name}) in {self.command} pressed [{button.label}]","files/log_discord.txt")


    def getData(self, page, stat, days, pageSize = database.embedPageSize):
        match stat:
            case 'Blocked%':
                data = database.getBlockedPercent(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average percentage of blocked lines ({days} days)"

            case 'Average OPB':
                data = database.getavgOPB(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Output per block ({days} days)"

            case 'Average OPM':
                data = database.getavgOPM(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Output per minute ({days} days)"

            case 'Average BPM':
                data = database.getavgBPM(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Blocks per minute ({days} days)"

            case 'Average SPM':
                data = database.getavgSPM(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average Sent per minute ({days} days)"

            case 'Time played':
                data = database.getTimePlayed(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize, isTime = True)
                title=f"Most active players ({days} days)" if page > 0 else f"Least active players ({days} days)"

            case 'Sent lines':
                data = database.getSent(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Total lines sent ({days} days)"
                
            case 'Netscores':
                data = database.getNetscores(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Netscores ({days} days)"

            case 'Average best combo':
                data = database.getCombos(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Average best combo ({days} days)"

            case 'Power':
                data = database.getPower(db, days=days)
                page = 1 if pageSize*(page - 1) > len(data) else page
                description=methods.getPage(page, data, pageSize = pageSize)
                title=f"Power ({days} days)"

            case other:
                return None, None
        
        return description, title


    @discord.ui.button(label="Day down", row = 0, style=discord.ButtonStyle.primary, emoji="⬇️") 
    async def day_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.days = max(1, self.days-1)
        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
                    description=description,
                    title=title),
            view=self
            )
        # log(f"{interaction.user.display_name} ({interaction.user.name}) in /{interaction.data['name']}: day down", 'files/log_discord.txt')

    @discord.ui.button(label="Page down", row = 1, style=discord.ButtonStyle.primary, emoji="⬅️") 
    async def page_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page = -1 if self.page == 1 else self.page - 1
        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
                    description=description,
                    title=title),
            view=self
            )
        # log(f"{interaction.user.display_name} ({interaction.user.name}) in /{interaction.data['name']}: page down", 'files/log_discord.txt')

    @discord.ui.button(label="Page up", row = 1, style=discord.ButtonStyle.primary, emoji="➡️") 
    async def page_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.page = 1 if self.page == -1 else self.page + 1
        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
                    description=description,
                    title=title),
            view=self
            )
        # log(f"{interaction.user.display_name} ({interaction.user.name}) in /{interaction.data['name']}: page up", 'files/log_discord.txt')

    @discord.ui.button(label="Day up", row = 0, style=discord.ButtonStyle.primary, emoji="⬆️") 
    async def day_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.logButton(interaction, button)
        self.days = min(database.dbDaysLimit, self.days+1)
        description, title = self.getData(self.page, self._stat, self.days)
        await interaction.response.edit_message(
            embed=discord.Embed(
                    color=0x0B3C52,
                    description=description,
                    title=title),
            view=self
            )
        # log(f"{interaction.user.display_name} ({interaction.user.name}) in /{interaction.data['name']}: day up", 'files/log_discord.txt')

@tree.command(description="Display a leaderboard of a selected stat."
              ,guild=guild
              )
@app_commands.describe(stat = "Stat of the leaderboard.",
                        days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
async def leaderboard(interaction: discord.Interaction, stat: str, days: app_commands.Range[int, 1, 30] = 7, page: int = 1):
    #Verification
    correct = await methods.checks(interaction)
    if not correct:
        return

    view = Leaderboard(interaction.user, stat, days, page)

    #Contents of message
    description, title = view.getData(page, stat, days)
    if not description:
        await interaction.response.send_message("Did you choose a stat?", ephemeral=True)
        return
    
    embed = discord.Embed(
            color=0x0B3C52,
            description=description,
            title=title)
    
    await interaction.response.send_message(embed=embed, view=view)
    view.message = await interaction.original_response()



@leaderboard.autocomplete('stat')
async def leaderboard_autocomplete(interaction: discord.Interaction, current: str):

    stats = sorted([
        'Average BPM',
        'Average best combo',
        'Netscores',
        'Average OPB',
        'Average OPM',
        'Average SPM',
        'Blocked%',
        'Sent lines',
        'Time played',
        'Power',
    ])
    return [
        app_commands.Choice(name=stat, value=stat)
        for stat in stats if current.lower() in stat.lower()
    ]





@tree.command(description="Descriptions of current commands."
              ,guild=guild
              )
async def help(interaction: discord.Interaction, about: str = 'Commands'):

    correct = await methods.checks(interaction)
    if not correct:
        return
    
    about = about if about in ['Commands', 'OPM/OPB', 'Power'] else 'Commands'

    match about:
        case 'Power':
            msg = """The amount of lines a player sends depends on the amount of players alive. Therefore, players will send more lines in bigger rooms. 'Power' is a stat that tries to give a player a score on their performance regardless of the size of the rooms they played in. The way this was done is by calculate the average OPM in the last 10 years for every roomsize.
For roomsizes between 2 and 9 Power in a round is calculated using the following table
```
roomsize: value
2: 37.8883647435868, 
3: 35.4831455255647, 
4: 40.1465889629567, 
5: 44.2602184213111, 
6: 48.575338292518, 
7: 50.649550305342, 
8: 51.9969119509592, 
9: 56.306414280463
```
with the following formula:
`(10/3) * OPM/roomsize_value`

For other roomsizes, the following formula is used:
`10 * OPM/(roomsize + 9.8)`

Power shown in `/stats` and `/leaderboard Power` is the average achieved in the range selected, not counting roomsize = 1. 
            """

        case 'OPM/OPB':
            msg = """OPM stands for Output per minute. The way to calculate is (linesSent + linesBlocked)/playDuration.
OPB stands for Output per block. The way to calculate is (lineSent + linesBlocked)/blocksPlaced."""

        case 'Commands':
            msg = """***/stats*** *[username] [days]* : Shows stats of a user in the last *[days]* days. By default, it will use your Discord display name as username, and in 7 days. If you can't find a user, try with an old username.

***/legacystats*** *[username]* : Shows all-time stats of an user. By default, it will use your Discord display name as username. If you can't find a user, try with an old username.

***/weeklybest*** : Shows a top 5 on SPM rounds and top 5 cheese times in the last 7 days. **Feel free to suggest things to add here**.

***/online*** : Shows a list of current players online.

***/leaderboard*** *[stat] [page] [days]* : Displays a leaderboard of a stat. Let Discord autocomplete show you what [stat] parameter can you choose. [page] can be negative to sort backwards.

***/rankings *** *[page] [fast]* : Current rank/scores. Doesn't work too well, specially at the end of the leaderboard. I've disabled negative page numbers for this reason. If `fast = True` it will display values stored in the database. If `fast = False` it will request them from gewaltig instead. No matter if this parameter is True or False, the positions on the leaderboard will be the same. 

Feel free to suggest additions/report bugs."""
            
    await interaction.response.send_message(msg, ephemeral = interaction.user.name != 'shayklos')

@help.autocomplete('about')
async def help_autocomplete(interaction: discord.Interaction, current: str):

    abouts = sorted([
        'Commands',
        'OPM/OPB',
        'Power'
    ])
    return [
        app_commands.Choice(name=about, value=about)
        for about in abouts if current.lower() in about.lower()
    ]


class ModalTest(discord.ui.Modal, title='Modal Test Title'):
    # Our modal classes MUST subclass `discord.ui.Modal`,
    # but the title can be whatever you want.

    # This will be a short input, where the user can enter their name
    # It will also have a placeholder, as denoted by the `placeholder` kwarg.
    # By default, it is required and is a short-style input which is exactly
    # what we want.
    name = discord.ui.TextInput(
        label='Label name here',
        placeholder='Placeholder name here',
    )

    # This is a longer, paragraph style input, where user can submit feedback
    # Unlike the name, it is not required. If filled out, however, it will
    # only accept a maximum of 300 characters, as denoted by the
    # `max_length=300` kwarg.
    field2 = discord.ui.TextInput(
        label='label feed here',
        style=discord.TextStyle.long,
        placeholder='tetete',
        required=False,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'what are you doing, {self.name.value}!', ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)



# @tree.command(guild=guild, description="description")
# async def test(interaction: discord.Interaction):
#     # Send the modal with an instance of our `Feedback` class
#     # Since modals require an interaction, they cannot be done as a response to a text command.
#     # They can only be done as a response to either an application command or a button press.
#     await interaction.response.send_modal(ModalTest())



@client.event
async def on_ready():
    await tree.sync(guild=None)
    await tree.sync(guild=discord.Object(id=202843125633384448))
    await tree.sync(guild=discord.Object(id=485229208457576472))
    print("Bot ready!")

@client.event
async def on_member_join(member: discord.Member):
    log(f"{member.display_name} ({member.name}) joined {member.guild.name}", "files/members.txt")

@client.event
async def on_member_remove(member: discord.Member):
    log(f"{member.display_name} ({member.name}) left {member.guild.name}", "files/members.txt")


@client.event 
async def on_message_edit(before : discord.Message, after : discord.Message):
    if before.author.id == client.user.id:
        return
    msg = f"BEFORE: [{before.guild.name}] {before.author.display_name} ({before.author.name}) : {before.content}"
    for attachment in before.attachments:
        msg += f" {attachment.url}"
    log(msg, "files/messages.txt")

    msg = f"AFTER: [{after.guild.name}] {after.author.display_name} ({after.author.name}) : {after.content}"
    for attachment in after.attachments:
        msg += f" {attachment.url}"
    log(msg, "files/messages.txt")

@client.event 
async def on_message_delete(message: discord.Message):
    msg = f"DELETE [{message.guild.name}] {message.author.display_name} ({message.author.name}) : {message.content}"
    for attachment in message.attachments:
        msg += f" {attachment.url}"
    log(msg, "files/messages.txt")


if __name__ == '__main__':
    client.run(TOKEN)



