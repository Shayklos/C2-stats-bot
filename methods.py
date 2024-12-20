import discord, json, asyncio
import database
from time import time
from bot import developerMode
from logger import log
from settings import *
from databaseexport import updateDatabase
from os.path import isfile, join
from pathlib import Path

def getPage(page, data, pageSize = embedPageSize, isTime = False):
    
    """data must be in format:
    data = [(userId, name, dataToBeShown)]
    dataToBeShwon will be ordered descending"""

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
    log(log_output, join('files', 'logs', 'discord.txt'))



async def checks(interaction: discord.Interaction):
    await logInteraction(interaction)
    with open(join('files', 'check_times.json'), "r") as file:
        data = json.load(file)
    if data.get("locked"):
        await interaction.response.send_message(f"Bot a bit busy! Try again in a minute.", ephemeral=True)
        return False
    with open(join('files', 'settings.json'), "r") as file:
        data = json.load(file)
    if interaction.user.name in data.get('approved_users').keys():
        return data.get('approved_users').get(interaction.user.name)
    if developerMode or interaction.user.name in admins:
        return True
    if interaction.command.name in admin_commands:
        return False
    if interaction.channel.guild is None or interaction.channel.name != 'stats':
        await interaction.response.send_message(f"Use the <#516686072537808897> channel! If you just want to use /stats, /legacystats or /challenges on yourself, you can just tell `shayklos`!", ephemeral=True)
        return False
    return True



def thousandsSeparator(n: int) -> str:
        #1212847128944 -> 1.212.847.128.944
        return f'{n:,}'

async def check_netscores(db):
    with open(join('files', 'check_times.json'), "r") as file:
        data = json.load(file)
    now = time()
    diff = now - data.get("NetscoreTime")

    if diff < 24*60*60: #A day
        return
    
    data["NetscoreTime"] = int(now)
    data["locked"] = True
    with open(join('files', 'check_times.json'), "w") as file:
        json.dump(data,file)

    # try:
    await database.add_recent_profile_data(db,7,True,True)
    # except Exception as e:
        # print(e)        
        # log("add_recent_profile_data failed!", e, "files/log_errors.txt")
        
    data["locked"] = False
    with open(join('files', 'check_times.json'), "w") as file:
        json.dump(data,file)

async def check_rankings(db):
    with open(join('files', 'check_times.json'), "r") as file:
        data = json.load(file)
    now = time()
    diff = now - data.get("RefreshRankingsTime")

    if diff < 7*24*60*60: #A week
        return
    
    data["RefreshRankingsTime"] = int(now)
    data["locked"] = True
    with open(join('files', 'check_times.json'), "w") as file:
        json.dump(data,file)

    await database.refresh_rankings(db,300)
    data["locked"] = False
    with open(join('files', 'check_times.json'), "w") as file:
        json.dump(data,file)

async def update_fulldb(path_to_db = join('files', 'fullCultris.db')):
    #Check if db exists
    if not isfile(path_to_db):
        return

    while True:
        with open(join('files', 'check_times.json'), "r") as file:
            data = json.load(file)
        
        now = time()
        diff = now - data.get("UpdateDBTime")

        if diff < 7*24*60*60: #A week
            return
        
        data["UpdateDBTime"] = int(now)
        data["locked"] = True
        with open(join('files', 'check_times.json'), "w") as file:
            json.dump(data,file)

        updateDatabase(join('files', 'cultris.db'), path_to_db)
        log("Full DB updated")
        
        data["locked"] = False
        with open(join('files', 'check_times.json'), "w") as file:
            json.dump(data,file)

        await asyncio.sleep(600)

def create_achievements_file(url):
    import urllib.request, csv
    with urllib.request.urlopen(url) as URL:
        data = json.load(URL)

    with open(join('files', 'extra', 'achievements.csv'), 'w', newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for element in data:
            writer.writerow(
                (data.get(element).get("title"), 
                 data.get(element).get("description"), 
                 data.get(element).get("points"),
                #  data.get(element).get("isPublic"),
                #  data.get(element).get("count"),                 
                 ))

def create_check_times_file():
    """
    Function executed at bot startup, checks if check_times.json exists and unlocks bot
    """
    file = Path(join("files","check_times.json"))

    if file.exists():
        #If bot is unlocked -> return
        with open(join("files","check_times.json"), 'r') as f:
            data: dict = json.load(f)
            if data and not data.get('locked'): return
        
        #If bot is locked -> unlock it, return
        data['locked'] = False
        with open(join("files","check_times.json"), 'w') as f:
            json.dump(data, f)

    #File does not exist, create it and place default values
    data = {
        "locked": False,
        "NetscoreTime": 0,
        "RefreshRankingsTime": 0,
        "UpdateDBTime": 0
    }

    #Check if this data is in settings.json (this could happen for legacy reasons)
    with open(join("files","settings.json"), 'r') as f:
        settings: dict = json.load(f)
    
    for key in data.keys():
        if settings.get(key): 
            data[key] = settings[key]
            settings.pop(key)

    #Remove these keys from settings as they are no longer needed
    with open(join("files","settings.json"), 'w') as f:
        json.dump(settings, f)

    #Finally, create file with this data
    with open(join("files","check_times.json"), 'w') as f:
        json.dump(data, f)



if __name__ == '__main__':
    create_check_times_file()
    pass