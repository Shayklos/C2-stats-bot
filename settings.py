import json

with open("files/settings.json", "r") as file:
    data = json.load(file)


dbDaysLimit                   = data.get("dbDaysLimit") if data.get("dbDaysLimit")                                     else 30
embedPageSize                 = data.get("embedPageSize") if data.get("embedPageSize")                                 else 20           
admins                        = data.get("admins") if data.get("admins")                                               else []
requiredMatchesCombos         = data.get("requiredMatchesCombos") if data.get("requiredMatchesCombos")                 else 15
requiredMatchesSPM            = data.get("requiredMatchesSPM") if data.get("requiredMatchesSPM")                       else 40
requiredMatchesBPM            = data.get("requiredMatchesBPM") if data.get("requiredMatchesBPM")                       else 40
requiredMatchesBlockedPercent = data.get("requiredMatchesBlockedPercent") if data.get("requiredMatchesBlockedPercent") else 40
requiredMatchesOPM            = data.get("requiredMatchesOPM") if data.get("requiredMatchesOPM")                       else 40
requiredMatchesOPB            = data.get("requiredMatchesOPB") if data.get("requiredMatchesOPB")                       else 40
timeformat                    = data.get("timeformat") if data.get("timeformat")                                       else r"%Y-%m-%dT%H:%M:%S"
BASE_USER_URL                 = data.get("BASE_USER_URL") if data.get("BASE_USER_URL")                                 else None
BASE_ROUNDS_URL               = data.get("BASE_ROUNDS_URL") if data.get("BASE_ROUNDS_URL")                             else None

if powerTableData := data.get("powerTable"):
    powerTableRange = data.get("powerTableRange")
    powerTable = {i : powerTableData[i - powerTableRange[0]] for i in range(powerTableRange[0], powerTableRange[1] + 1)}
else:
    powerTable = {2: 37.8883647435868, 3: 35.4831455255647, 4: 40.1465889629567, 5: 44.2602184213111, 6: 48.575338292518, 7: 50.649550305342, 8: 51.9969119509592, 9: 56.306414280463}
