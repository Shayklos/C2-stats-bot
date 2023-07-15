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
            description += f"{r}. [{element[1]}](https://gewaltig.net/ProfileView/{element[0]}) {element[2]}\n"
        r+=1

    return description


#TODO Netscores
#TODO Clean up stats. Decide how to divide data


@tree.command(guild=discord.Object(id=GUILD_ID), description="Returns stats of a user. If you can't find the user, maybe try with an old nickname?")
@app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
# @app_commands.rename(username='user')
async def stats(interaction: discord.Interaction, username: str=None):
    #TODO? searches for old username until a routine like add_netscores updates the username
    if not username:
        username = interaction.user.display_name
    ratio, userId, user = fuzzysearch(db, username)
    print(ratio, userId, user)
    msg = None
    if ratio < 100:
        msg = f"No user found with name \'{username}\'. Did you mean \'{user}\'?"
        
    

    player = player_stats(db, userId)
    timeStats = time_based_stats(db, userId)
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

    embed.add_field(name="Best Combo", value=player["maxCombo"], inline=True)
    embed.add_field(name="Games", value=player["playedRounds"], inline=True)
    embed.add_field(name="Wins", value=player["wins"], inline=True)

    if player["maxBPM"]:
        embed.add_field(name="Max BPM", value=round(player["maxBPM"], 1), inline=True)
        embed.add_field(name="Avg BPM", value=round(player["avgBPM"], 1), inline=True)
        embed.add_field(name="Total Hours", value=f"{player['playedMin']/60:.1f}", inline=True)
    if timeStats["avgBPM"]:
        embed.add_field(name="Avg BPM (30d)", value=round(timeStats["avgBPM"], 1), inline=True)
    if timeStats["avgCombo"]:    
        embed.add_field(name="Avg Combo (30d)", value=round(timeStats["avgCombo"], 1), inline=True)
    if timeStats["avgSPM"]:
        embed.add_field(name="Avg SPM (30d)", value=round(timeStats["avgSPM"], 1), inline=True)
    if timeStats["blockedpercent"]:
        embed.add_field(name="Blocked% (30d)", value=round(timeStats["blockedpercent"], 1), inline=True)
    if timeStats["winrate"]:
        embed.add_field(name="Winrate (30d)", value=round(timeStats["winrate"], 1), inline=True)
    if timeStats["mins"]:
        embed.add_field(name="Minutes played (30d)", value=round(timeStats["mins"], 1), inline=True)
    else:
        embed.add_field(name="Minutes played (30d)", value="0", inline=True)
    
    embed.set_author(name = '‎', icon_url = f"https://www.gravatar.com/avatar/{player['gravatarHash']}?d=https://i.imgur.com/Gms07El.png")
    await interaction.response.send_message(msg, embed=embed)


@tree.command(guild=discord.Object(id=GUILD_ID))
async def weeklybest(interaction: discord.Interaction):
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
                    f"""{top5Cheese[0][0]} - {round(top5Cheese[0][1])}
{top5Cheese[1][0]} - {round(top5Cheese[1][1],2)}
{top5Cheese[2][0]} - {round(top5Cheese[2][1],2)}
{top5Cheese[3][0]} - {round(top5Cheese[3][1],2)}
{top5Cheese[4][0]} - {round(top5Cheese[4][1],2)}

""", inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(guild=discord.Object(id=GUILD_ID),description="Shows which users are online right now.")
async def online(interaction: discord.Interaction):
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


@tree.command(guild=discord.Object(id=GUILD_ID),
              description="Sorts the players according to who has played the most in a recent period of time.")
@app_commands.describe(days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
async def active(interaction: discord.Interaction, 
                 page: int = 1,
                 days: Literal[1,3,7,10,14,15,20,21,25,28,30]=7 
                 ):   

    embed = discord.Embed(
            color=0x0B3C52,
            description=getPage(page, activePlayers(db, days=days), isTime = True),
            title=f"Most active players ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)


@tree.command(guild=discord.Object(id=GUILD_ID),
              description="Sorts the players according to who has played the most in a recent period of time.")
@app_commands.describe(days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
async def combo(interaction: discord.Interaction, 
                 page: int = 1,
                 days: Literal[1,3,7,10,14,15,20,21,25,28,30]=7 
                 ):   

@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=GUILD_ID))
    print("Ready!")

client.run(TOKEN)
