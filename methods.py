import discord, json
import database
from time import time
from bot import developerMode
from logger import log
from settings import *


def getPage(page, data, pageSize = embedPageSize, isTime = False):
    
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



async def checks(interaction: discord.Interaction):
    await logInteraction(interaction)
    with open("files/settings.json", "r") as file:
        data = json.load(file)
    if data.get("locked"):
        await interaction.response.send_message(f"Bot a bit busy! Try again in a minute.", ephemeral=True)
        return False
    if developerMode or interaction.user.name in admins:
        return True
    if interaction.channel.name != 'stats':
        await interaction.response.send_message(f"Use the <#516686072537808897> channel!", ephemeral=True)
        return False
    return True



def thousandsSeparator(n: int) -> str:
        #1212847128944 -> 1.212.847.128.944
        return f'{n:,}'

def check_netscores(db):
    with open("files/settings.json", "r") as file:
        data = json.load(file)
    now = time()
    diff = now - data.get("time")

    if diff > 24*60*60:
        data["time"] = int(now)
        data["locked"] = True
        with open("files/settings.json", "w") as file:
            json.dump(data,file)

        database.add_recent_profile_data(db,7,True,True)
        data["locked"] = False
        with open("files/settings.json", "w") as file:
            json.dump(data,file)

if __name__ == '__main__':
    check_netscores(1)
