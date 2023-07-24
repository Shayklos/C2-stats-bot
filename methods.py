import discord, bot

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


def isStatsChannel(interaction: discord.Interaction) -> bool:
    if interaction.user.name in ['yoozenji', 'shayklos', 'forbiddenazalea']:
        return True
    if bot.developerMode:
        return True
    if interaction.channel.name != 'stats':
        return False
    return True


def thousandsSeparator(n: int) -> str:
        #1212847128944 -> 1.212.847.128.944
        return f'{n:,}'.replace(',', '.')

