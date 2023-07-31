import json

with open("files/settings.json", "r") as file:
    data = json.load(file)


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

