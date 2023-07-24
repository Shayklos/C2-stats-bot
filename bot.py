import asyncio
import os
import discord
from discord import app_commands
from dotenv import load_dotenv
import database, sqlite3
import methods
from logger import *
import urllib.request
import traceback 

developerMode = False


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')


intents = discord.Intents.default()
client  = discord.Client(intents=intents, activity=discord.Game(name="Cultris II"))
tree    = app_commands.CommandTree(client)
guild   = discord.Object(id=GUILD_ID) if developerMode else None
db = sqlite3.connect(r"files\cultris.db", check_same_thread=False)



async def logInteraction(interaction:discord.Interaction):
    log_output = f"{interaction.user.display_name} ({interaction.user.name}) used /{interaction.data['name']}"
    if interaction.data.get('options'):
        for option in interaction.data['options']:
            if option.get('value'):
                log_output += f" [{option['name']} = {option['value']}]"
            else:
                log_output += f" {option['name']}"
                if option.get('options'):
                    for suboption in option.get('options'):
                        log_output += f" [{suboption['name']} = {suboption['value']}]"


    log(log_output, "files/log_discord.txt")


@tree.command(description="Returns stats of a user. If you can't find the user, maybe try with an old nickname?"
              ,guild=guild
              )
@app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
async def stats(interaction: discord.Interaction, username: str=None, days: app_commands.Range[int, 1, 30] = 7):
    
    try:
        await logInteraction(interaction)
        if not methods.isStatsChannel(interaction):
            await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
            return
        
        if not username:
            username = interaction.user.display_name
        ratio, userId, user = database.fuzzysearch(db, username.lower())
        msg = None
        if ratio != 100:
            msg = f"No user found with name \'{username}\'. Did you mean \'{user}\'?"

        timeStats = database.time_based_stats(db, userId, days=days)
        player = database.player_stats(db, userId)
        netscore, netscoreDays = database.getNetscore(db, userId)
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
        await interaction.response.send_message(msg, embed=embed)
    except Exception as e:
        print(e)
        log(traceback.format_exc())


@tree.command(description="Returns all-time stats of a user. If you can't find the user, maybe try with an old nickname?"
              ,guild=guild
              )
@app_commands.describe(username='Ingame username of the player you\'re looking for. Leave empty to use your Discord display name.')
async def legacystats(interaction: discord.Interaction, username: str=None):
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
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



@tree.command(
        guild=guild,
        )
async def weeklybest(interaction: discord.Interaction):
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
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

""", inline=False)

    embed.add_field(name = "Top 5 Cheese times (7d)", value = 
                    f"""**{top5Cheese[0][0]}** - {round(top5Cheese[0][1],2)}
**{top5Cheese[1][0]}** - {round(top5Cheese[1][1],2)}
**{top5Cheese[2][0]}** - {round(top5Cheese[2][1],2)}
**{top5Cheese[3][0]}** - {round(top5Cheese[3][1],2)}
**{top5Cheese[4][0]}** - {round(top5Cheese[4][1],2)}

""", inline=False)
    await interaction.response.send_message(embed=embed)



@tree.command(description="Shows which users are online right now."
              ,guild=guild
              )
async def online(interaction: discord.Interaction):
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    players = database.getPlayersOnline(db)
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











# async def hello(interaction: discord.Interaction, message: discord.User):
#     await interaction.response.send_message(f"Hey {message.author.mention}!")

# hello_context_menu = app_commands.ContextMenu(
#     name='Say Hello',
#     callback=hello,
# )
# tree.add_command(hello_context_menu)

group = app_commands.Group(name = 'leaderboard', description= "description")

@group.command(description="Leaderboard of average best combo")
@app_commands.describe(days = "Number of days the period of time has (by default 7)",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards")
async def avgcombos(interaction: discord.Interaction, page: int=1, days: app_commands.Range[int, 1, 30] = 7): 
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=methods.getPage(page, database.getCombos(db, days=days)),
            title=f"Average best combo ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)


@group.command(description="Shows how much people have gained in a recent period of time.")
@app_commands.describe(days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
async def netscores(interaction: discord.Interaction, page: int=1, days: app_commands.Range[int, 2, 7] = 7):
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=methods.getPage(page, database.getNetscores(db, days=days)),
            title=f"Netscores ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)


@group.command(description="Shows how much lines have people sent in a period of time.")
@app_commands.describe(days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Negative sorting disabled.")
async def sent(interaction: discord.Interaction, page: int=1, days: app_commands.Range[int, 1, 30] = 7):
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=methods.getPage(page, database.getSent(db, days=days)),
            title=f"Total lines sent ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)


@group.command(description="Displays current leaderboard. Doesn't work too well... the positions of may not be accurate.")
@app_commands.describe(page = "The page you want to see (by default 1). Negative page numbers are not allowed here.",
                       fast = "If fast = True then it will take values stored in database. If fast = False then it will get scores from gewaltig, taking way longer.")
async def rankings(interaction: discord.Interaction, page: app_commands.Range[int, 1] = 1, fast: bool = True):
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    pageSize = 20 
    start = pageSize * (page - 1) + 1
    end = start + pageSize -1
    data = database.getRankings(db, start, end, fast)
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


@group.command(description="Sorts the players according to who has played the most in a recent period of time.")
@app_commands.describe(days = "Number of days the period of time has (by default 7).",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards.")
async def active(interaction: discord.Interaction, 
                 page: int = 1,
                 days: app_commands.Range[int, 1, 30] = 7
                 ): 
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=methods.getPage(page, database.activePlayers(db, days=days), isTime = True),
            title=f"Most active players ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)


@group.command(description="Leaderboard of average SPM (Sent lines per minute)")
@app_commands.describe(days = "Number of days the period of time has (by default 7)",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards")
async def avgspm(interaction: discord.Interaction, page: int=1, days: app_commands.Range[int, 1, 30] = 7):
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=methods.getPage(page, database.getavgSPM(db, days=days)),
            title=f"Average SPM ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)


@group.command(description="Leaderboard of average BPM (Blocks placed per minute)")
@app_commands.describe(days = "Number of days the period of time has (by default 7)",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards")
async def avgbpm(interaction: discord.Interaction, page: int=1, days: app_commands.Range[int, 1, 30] = 7):
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=methods.getPage(page, database.getavgBPM(db, days=days)),
            title=f"Average BPM ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)



@group.command(description="Leaderboard of average blocked% (Lines blocked/Lines Received)")
@app_commands.describe(days = "Number of days the period of time has (by default 7)",
                       page = "The page you want to see (by default 1). Use negative numbers to sort backwards")
async def blocked(interaction: discord.Interaction, page: int=1, days: app_commands.Range[int, 1, 30] = 7):
    await logInteraction(interaction)
    if not methods.isStatsChannel(interaction):
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return
    embed = discord.Embed(
            color=0x0B3C52,
            description=methods.getPage(page, database.getBlockedPercent(db, days=days)),
            title=f"Average percentage of blocked lines ({days} days)"
        )
    
    await interaction.response.send_message(embed=embed)

tree.add_command(group, guild=guild)

@tree.command(description="Descriptions of current commands."
              ,guild=guild
              )
async def help(interaction: discord.Interaction):
    await logInteraction(interaction)
    msg = """***/stats*** *[username] [days]* : Shows stats of a user in the last *[days]* days. By default, it will use your Discord display name as username, and in 7 days. If you can't find a user, try with an old username.

***/legacystats*** *[username]* : Shows all-time stats of an user. By default, it will use your Discord display name as username. If you can't find a user, try with an old username.

***/weeklybest*** : Shows a top 5 on SPM rounds and top 5 cheese times in the last 7 days. Right now it might miss some cheese times! Will be fixed soon. **Feel free to suggest things to add here**.

***/online*** : Shows a list of current players online.

__**Stats leaderboards**__

These commands show a leaderboard in a single stat in a recent period of time. 
You can choose the number of [days] this leaderboard will consider (normally up to 30 days). You can also select the [page] number, using negative numbers to sort backwards.

***/leaderboard active*** *[page] [days]* : Time played
***/leaderboard avgcombos*** *[page] [days]* : Average best combo
***/leaderboard avgspm*** *[page] [days]* : Average SPM
***/leaderboard avgbpm*** *[page] [days]* : Average BPM
***/leaderboard netscores*** *[page] [days]* : Score yesterday - Score [days] days ago (up to a week). Use /stats to see your real netscore now.
***/leaderboard sent*** *[page] [days]* : Total sent lines.
***/leaderboard rankings *** *[page] [fast]* : Current rank/scores. Doesn't work too well, specially at the end of the leaderboard. I've disabled negative page numbers for this reason. If `fast = True` it will display values stored in the database. If `fast = False` it will request them from gewaltig instead. No matter if this parameter is True or False, the positions on the leaderboard will be the same. 
***/leaderboard active*** *[page] [days]* : Time played

Feel free to suggest additions/report bugs.
"""
    await interaction.response.send_message(msg)



@client.event
async def on_ready():
    await tree.sync(guild=None)
    await tree.sync(guild=discord.Object(id=202843125633384448))
    print("Bot ready!")


if __name__ == '__main__':
    client.run(TOKEN)



