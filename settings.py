import json
import os
from dotenv import load_dotenv

load_dotenv() 
with open(os.path.join('files','settings.json'), "r") as file:
    data = json.load(file)

gatherDataRefreshRate         = data.get("gatherDataRefreshRate") if data.get("gatherDataRefreshRate")                 else 30
dbDaysLimit                   = data.get("dbDaysLimit") if data.get("dbDaysLimit")                                     else 30
embedPageSize                 = data.get("embedPageSize") if data.get("embedPageSize")                                 else 20  
botTimeout                    = data.get("botTimeout") if data.get("botTimeout")                                       else 120  
admins                        = data.get("admins") if data.get("admins")                                               else []
requiredMatchesCombos         = data.get("requiredMatchesCombos") if data.get("requiredMatchesCombos")                 else 15
requiredMatchesSPM            = data.get("requiredMatchesSPM") if data.get("requiredMatchesSPM")                       else 40
requiredMatchesBPM            = data.get("requiredMatchesBPM") if data.get("requiredMatchesBPM")                       else 40
requiredMatchesBlockedPercent = data.get("requiredMatchesBlockedPercent") if data.get("requiredMatchesBlockedPercent") else 40
requiredMatchesOPM            = data.get("requiredMatchesOPM") if data.get("requiredMatchesOPM")                       else 40
requiredMatchesOPB            = data.get("requiredMatchesOPB") if data.get("requiredMatchesOPB")                       else 40
requiredMatchesPower          = data.get("requiredMatchesPower") if data.get("requiredMatchesPower")                   else 40
requiredMatchesEfficiency     = data.get("requiredMatchesEfficiency") if data.get("requiredMatchesEfficiency")         else 40
requiredMatchesComboCount     = data.get("requiredMatchesComboCount") if data.get("requiredMatchesComboCount")         else 40
timeformat                    = data.get("timeformat") if data.get("timeformat")                                       else r"%Y-%m-%dT%H:%M:%S"
BASE_USER_URL                 = os.getenv("BASE_USER_URL")
BASE_ROUNDS_URL               = os.getenv("BASE_ROUNDS_URL")
LIVEINFO_URL                  = os.getenv("LIVEINFO_URL")
deleteUserData                = data.get("deleteUserData") if data.get("deleteUserData")                               else True
commandCooldown               = data.get("commandCooldown") if data.get("commandCooldown")                             else 120
roundsUserdataDirectory       = data.get("roundsUserdataDirectory").replace('/', os.sep) if data.get("roundsUserdataDirectory") else os.path.join("files", "userdata", "rounds") + os.sep
online_message_frequency      = data.get("online_message_frequency") if data.get("online_message_frequency")           else 30

if powerTableData := data.get("powerTable"):
    powerTableRange = data.get("powerTableRange")
    powerTable = {i : powerTableData[i - powerTableRange[0]] for i in range(powerTableRange[0], powerTableRange[1] + 1)}
else:
    powerTable = {2: 37.8883647435868, 3: 35.4831455255647, 4: 40.1465889629567, 5: 44.2602184213111, 6: 48.575338292518, 7: 50.649550305342, 8: 51.9969119509592, 9: 56.306414280463}

multiplier = {i : powerTable.get(2)/powerTable.get(i) for i in range(powerTableRange[0], powerTableRange[1] + 1)}

COLOR_Default = int(data.get("COLOR_Default"), 16) if data.get("COLOR_Default") else 0x0B3C52
COLOR_Yellow  = int(data.get("COLOR_Yellow"), 16) if data.get("COLOR_Yellow")   else 0xFFFF70
COLOR_Red     = int(data.get("COLOR_Red"), 16) if data.get("COLOR_Red")         else 0xFF0000
COLOR_Grey    = int(data.get("COLOR_Grey"), 16) if data.get("COLOR_Grey")       else 0x777777

botzilla_name           = data.get("botzilla_name")           if data.get("botzilla_name")           else "botzilla"
botzilla_check_for_name = data.get("botzilla_check_for_name") if data.get("botzilla_check_for_name") else True
botzilla_check_for_java = data.get("botzilla_check_for_java") if data.get("botzilla_check_for_java") else False
linux_terminal          = data.get("linux_terminal")          if data.get("linux_terminal")          else "tmux"