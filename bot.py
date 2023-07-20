import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from database import *
import urllib.request
from typing import Literal



load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')

intents = discord.Intents.default()
client  = discord.Client(intents=intents)
tree    = app_commands.CommandTree(client)


def getPage(page, data, pageSize = 20, isTime = False):
    
    #data must be in format:
    #data = [(userId, name, dataToBeShown)]
    #dataToBeShwon will be ordered descending

    if pageSize*(page - 1) > len(data):
        page = -1
    if page < 0:
        page = -page
        data = sorted(
                    data, key=lambda element: element[2] 
                )

    start = pageSize * (page - 1)
    end = start + pageSize
    r = start + 1
    description = ""
    for element in data[start:end]:
        if isTime:
            description += f"{r}. [{element[1]}](https://gewaltig.net/ProfileView/{element[0]}) {element[2]//3600:.0f}h {element[2] % 3600 /60:.0f}m\n"
        else:
            if type(element[2]) is str or type(element[2]) is int: 
                description += f"{r}. [{element[1]}](https://gewaltig.net/ProfileView/{element[0]}) {element[2]}\n"
            else:
                description += f"{r}. [{element[1]}](https://gewaltig.net/ProfileView/{element[0]}) {element[2]:.1f}\n"
        r+=1

    return description


#TODO Netscores
#TODO Clean up stats. Decide how to divide data
#guild=discord.Object(id=GUILD_ID),

@tree.command(description="Returns stats of a user. If you can't find the user, maybe try with an old nickname?")
@app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
async def stats(interaction: discord.Interaction, username: str=None, days: app_commands.Range[int, 1, 30] = 7):
    if interaction.channel.name != 'stats':
        print(interaction.channel.mention)
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    
    if not username:
        username = interaction.user.display_name
    ratio, userId, user = fuzzysearch(db, username)
    msg = None
    if ratio != 100:
        msg = f"No user found with name \'{username}\'. Did you mean \'{user}\'?"

    timeStats = time_based_stats(db, userId, days=days)
    player = player_stats(db, userId)
    netscore, netscoreDays = getNetscore(db, userId)
    # print(netscore, netscoreDays)
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

        embed.add_field(name="Max BPM", value=round(timeStats["bestBPM"], 1), inline=True)
        embed.add_field(name="Avg BPM", value=round(timeStats["avgBPM"], 1), inline=True)
        embed.add_field(name="Blocked%", value=f"{timeStats['blockedpercent']:.1f}%", inline=True)
        if netscoreDays:
            if netscoreDays == days:
                embed.add_field(name = 'Netscore', value = round(player['score'] - netscore,1))
            else:
                embed.add_field(name = f'Netscore ({netscoreDays}d)', value = round(player['score'] - netscore,1))
    
    else:
        embed.add_field(name="Minutes played", value="0", inline=True)
    
    embed.set_thumbnail(url=f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png")
    await interaction.response.send_message(msg, embed=embed)



@tree.command(description="Returns all-time stats of a user. If you can't find the user, maybe try with an old nickname?")
@app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
async def legacystats(interaction: discord.Interaction, username: str=None):
    if interaction.channel.name != 'stats':
        print(interaction.channel.mention)
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    if not username:
        username = interaction.user.display_name
    ratio, userId, user = fuzzysearch(db, username) #ej (80, 5840, Shay)

    msg = None
    if ratio != 100:
        msg = f"No user found with name \'{username}\'. Did you mean \'{user}\'?"
        
    
    
    player = player_stats(db, userId)
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
        embed.add_field(name="Wins", value=player["wins"], inline=True)
        embed.add_field(name="Games", value=f"{player['playedRounds']} ({player['playedRoundsStandard']} in Standard)", inline=True)

        embed.add_field(name="Max BPM", value=round(player["maxBPM"], 1), inline=True)
        embed.add_field(name="Avg BPM", value=round(player["avgBPM"], 1), inline=True)
        embed.add_field(name="Total Hours", value=f"{player['playedMin']/60:.1f}h", inline=True)

        embed.add_field(name="Standard time", value=f"{player['standardTime']/3600:.1f}h", inline=True)
        embed.add_field(name="Cheese time", value=f"{player['cheeseTime']/3600:.1f}h", inline=True)
        embed.add_field(name="Teams time", value=f"{player['teamsTime']/3600:.1f}h", inline=True)

        embed.add_field(name="Received lines", value=player["linesGot"], inline=True)
        embed.add_field(name="Sent lines", value=player["linesSent"], inline=True)
        embed.add_field(name="Blocked lines", value=player["linesBlocked"], inline=True)

        embed.add_field(name="Sum of Max Combos", value=player["comboSum"], inline=True)
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



@tree.command()
async def weeklybest(interaction: discord.Interaction):
    if interaction.channel.name != 'stats':
        print(interaction.channel.mention)
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    top5SPM, top5Cheese = weekly_best(db)
    embed = discord.Embed(
            title="Weekly Best",
            color=0x0B3C52,
        )
    embed.add_field(name = "Top 5 SPM (7d)", value = 
                    f"""{top5SPM[0][0]} - {round(top5SPM[0][1])}
{top5SPM[1][0]} - {round(top5SPM[1][1])}
{top5SPM[2][0]} - {round(top5SPM[2][1])}
{top5SPM[3][0]} - {round(top5SPM[3][1])}
{top5SPM[4][0]} - {round(top5SPM[4][1])}

""", inline=False)

    embed.add_field(name = "Top 5 Cheese times (7d)", value = 
                    f"""{top5Cheese[0][0]} - {round(top5Cheese[0][1],2)}
{top5Cheese[1][0]} - {round(top5Cheese[1][1],2)}
{top5Cheese[2][0]} - {round(top5Cheese[2][1],2)}
{top5Cheese[3][0]} - {round(top5Cheese[3][1],2)}
{top5Cheese[4][0]} - {round(top5Cheese[4][1],2)}

""", inline=False)
    await interaction.response.send_message(embed=embed)



@tree.command(description="Shows which users are online right now.")
async def online(interaction: discord.Interaction):
    if interaction.channel.name != 'stats':
        print(interaction.channel.mention)
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    players = getPlayersOnline(db)
    string = ""
    for player in players:
        string += player + ", "
    embed = discord.Embed(
            color=0x0B3C52,
            description=string[:-2],
            title="Players online"
        )
    # embed.add_field(name ='Players online', value = string[:-2])

    await interaction.response.send_message(embed=embed)



@tree.command(description="Sorts the players according to who has played the most in a recent period of time.")
@app_commands.describe(days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
async def active(interaction: discord.Interaction, 
                 page: int = 1,
                 days: app_commands.Range[int, 1, 30] = 7
                 ): 
    if interaction.channel.name != 'stats':
        print(interaction.channel.mention)
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=getPage(page, activePlayers(db, days=days), isTime = True),
            title=f"Most active players ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)



@tree.command(description="Shows which users are online right now.")
@app_commands.describe(days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
async def combos(interaction: discord.Interaction, page: int=1, days: app_commands.Range[int, 1, 30] = 7):
    if interaction.channel.name != 'stats':
        print(interaction.channel.mention)
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=getPage(page, getCombos(db, days=days)),
            title=f"Average combo ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)




@tree.command(description="Shows how much people have gained in a recent period of time.")
@app_commands.describe(days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
async def netscores(interaction: discord.Interaction, page: int=1, days: app_commands.Range[int, 2, 7] = 7):
    if interaction.channel.name != 'stats':
        print(interaction.channel.mention)
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=getPage(page, getNetscores(db, days=days)),
            title=f"Netscores    ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)



@tree.command(description="Shows how much lines have people sent in a period of time.")
@app_commands.describe(days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
async def sent(interaction: discord.Interaction, page: int=1, days: app_commands.Range[int, 1, 30] = 7):
    if interaction.channel.name != 'stats':
        print(interaction.channel.mention)
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=getPage(page, getSent(db, days=days)),
            title=f"Total lines sent ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)




@tree.command(description="Shows current leaderboard. Doesn't work too well... while scores are truthful, ranks may not be.")
@app_commands.describe(page = "The page you want to see (by default 1). Negative page numbers are not allowed here.",
                       fast = "If fast = True then it will take values stored in database. If fast = False then it will get scores from gewaltig, taking way longer.")
async def rankings(interaction: discord.Interaction, page: app_commands.Range[int, 1] = 1, fast: bool = True):
    if interaction.channel.name != 'stats':
        print(interaction.channel.mention)
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    pageSize = 20 
    start = pageSize * (page - 1) + 1
    end = start + pageSize -1
    data = getRankings(db, start, end, fast)
    description = ""
    for element in data:
        description += f"{start}. [{element[1]}](https://gewaltig.net/ProfileView/{element[0]}) {element[2]}\n"
        start+=1

    embed = discord.Embed(
            color=0x0B3C52,
            description=description,
            title=f"Leaderboard"
        )
    await interaction.response.send_message(embed=embed)


@tree.command(description="Descriptions of current commands.")
async def help(interaction: discord.Interaction):
    msg = """***/stats*** *[username] [days]* : Shows stats of a user in the last *[days]* days. By default, it will use your Discord display name as username, and in 7 days. If you can't find a user, try with an old username.

***/legacystats*** *[username]* : Shows all-time stats of an user. By default, it will use your Discord display name as username. If you can't find a user, try with an old username.

***/weeklybest*** : Shows a top 5 on SPM rounds and top 5 cheese times in the last 7 days. Right now it might miss some cheese times! Will be fixed soon. **Feel free to suggest things to add here**.

***/online*** : Shows a list of current players online.

__**Stats leaderboards**__

These commands show a leaderboard in a single stat in a recent period of time. 
You can choose the number of [days] this leaderboard will consider (normally up to 30 days). You can also select the [page] number, using negative numbers to sort backwards.

***/active*** *[page] [days]* : Time played
***/combos*** *[page] [days]* : Average best combo
***/netscores*** *[page] [days]* : Score yesterday - Score [days] days ago (up to a week). Use /stats to see your real netscore now.
***/sent*** *[page] [days]* : Total sent lines.
***/leaderboard*** *[page] [fast]* : Current rank/scores. Doesn't work too well, specially at the end of the leaderboard. I've disabled negative page numbers for this reason. If `fast = True` it will display values stored in the database. If `fast = False` it will request them from gewaltig instead. No matter if this parameter is True or False, the positions on the leaderboard will be the same. 


Feel free to suggest additions/report bugs.
"""
    await interaction.response.send_message(msg)


@client.event
async def on_ready():
    await tree.sync()
    print("Ready!")


client.run(TOKEN)



