import sqlite3
import urllib.request, json
from constants import * 
from datetime import datetime,timedelta
from pytz import timezone
from timer import *

db = sqlite3.connect(r"files\cultris.db")

# db.execute("CREATE TABLE Matches(roundId INT primary key, start DATETIME, ruleset TINYINT, speedLimit INT)")

# db.execute("""CREATE TABLE Rounds(
#     roundId INT,
#     userId INT,
#     guestName VARCHAR(32),
#     linesGot UNSIGNED SMALLINT,
#     linesSent UNSIGNED SMALLINT,
#     linesBlocked UNSIGNED SMALLINT,
#     blocks UNSIGNED SMALLINT,
#     maxCombo UNSIGNED TINYINT,
#     playDuration DOUBLE,
#     team UNSIGNED TINYINT)
#     """)
# 
# db.execute("""
# CREATE TABLE Users(
#   userId UNSIGNED INTEGER,
#   name VARCHAR(255),
#   ...
# 
# 
# )
# """)
74.8749852827486
74.87498528274857

def oldest_round(db):
    res = db.execute("select min(roundId) from Matches")
    return res.fetchone()[0]

def newest_round(db):
    res = db.execute("select max(roundId) from Matches")
    return res.fetchone()[0]

@log_time
def add_new_rounds(db):
    """
    Adds to the database rounds played that are not already there.
    Relies on having data already.
    """
    first_round = newest_round(db)+1 #First round that it is not in the db
    roundN = first_round
    empty = False
    count = 0
    while not empty:
        try:
            url = BASE_ROUNDS_URL+str(roundN)
            with urllib.request.urlopen(url) as URL:
                data = json.load(URL)

            if not data:
                empty = True
                break

            query1 = "insert into Matches values (?, ?, ?, ?)"
            query2 = "insert into Rounds values (?,?,?,?,?,?,?,?,?,?)"
            parameters1, parameters2 = [], []
            for round in data:
                round_param1 = (
                    round.get("roundId"), 
                    datetime.strptime(round.get('start').split('.')[0], timeformat), #ignoring ms
                    round.get("ruleset"), 
                    round.get("speedLimit")
                )
                parameters1.append(round_param1)
                
                players = round.get("players")
                for player in players:
                    params2 = (round.get("roundId"),
                    player.get("userId"),
                    player.get("guestName"),
                    player.get("linesGot"),
                    player.get("linesSent"),
                    player.get("linesBlocked"),
                    player.get("blocks"),
                    player.get("maxCombo"),
                    player.get("playDuration"),
                    player.get("team"),
                    )
                    parameters2.append(params2)
                
                count += 1
                    
            db.executemany(query1,parameters1)
            db.executemany(query2,parameters2)
            db.commit()
            roundN += 1000
        except Exception as e:
            print(e)
            roundN = newest_round(db)+1
    
    log(f"Added {count} matches.")

    # #Returns new Rounds data (should probably separate this from the rest of the function)         
    # res = db.execute("select max(roundId) from Matches")
    # last_round = res.fetchone()[0]
    # db.execute("select * from")

@log_time
def delete_old_data(db, days=30):
    date_now = datetime.now(tz = timezone('UTC'))

    db = sqlite3.connect(r"files\cultris.db")
    res = db.execute("select max(roundId) from Matches where start < (?)", (date_now-timedelta(days=days),))
    id = res.fetchone()[0]

    res = db.execute("select count(roundId) from Matches where roundId < (?)", (id,))
    db.execute("delete from Matches where roundId < (?)", (id,))
    db.execute("delete from Rounds where roundId < (?)", (id,))
    log(f"Deleted {res.fetchone()[0]} matches.")
    db.commit()

# def data_between_rounds(db, old_round, new_round):
#     res = db.execute("select * from rounds where (?) < roundId and roundId <= (?)", (old_round, new_round))
#     return res.fetchall()

def player_dict_one(player_rounds):
    #TODO remove roundId
    conversion_table = ["roundId", "userId", "guestName", "linesGot", "linesSent", "linesBlocked", "blocks", "maxCombo", "playDuration", "team"]
    return {conversion_table[i] : player_rounds[i] for i in range(len(conversion_table))} 

@log_time
def process_data(db, oldRound, newRound):
    rounds = db.execute("select * from rounds where roundId between ? and ?", (oldRound, newRound))
    rulesets = db.execute("select ruleset from matches where roundId between ? and ?", (oldRound, newRound))
    # rounds element example
    # ["roundId","userId","name","got","sent","blocked","blocks", "maxCombo", "playDuration", "team"]
    # (12421684,  None,   'Mark', 25,    47,     14,      78,         10,     39.1243,          None), 

    not_finished = True
    current_roundId = None
    count = 0
    while not_finished:
        raw_round = rounds.fetchone()
        if raw_round is None:
            not_finished = True
            break
        elif raw_round[0] != current_roundId:
            current_roundId = raw_round[0]
            ruleset = rulesets.fetchone()[0]
        
        round = player_dict_one(raw_round)

        #basically a 'choose your own adventure' query
        query = "UPDATE Users Set blocksPlaced = blocksPlaced + ?"
        params = [round["blocks"]]

        if not round["userId"]:
            continue

        if round["team"] is not None:
            query += ", teamsTime = teamsTime + ?"
            params.append(round["playDuration"])
        if ruleset == 1:
            query += ", cheeseTime = cheeseTime + ?"
            params.append(round["playDuration"])
        elif ruleset == 0:
            if round["maxCombo"] < 10:
                pass
            elif round["maxCombo"] == 10:
                query += ", \"10s\" = \"10s\" + 1"
            elif round["maxCombo"] == 11:
                query += ", \"11s\" = \"11s\" + 1"
            elif round["maxCombo"] == 12:
                query += ", \"12s\" = \"12s\" + 1"
            elif round["maxCombo"] == 13:
                query += ", \"13s\" = \"13s\" + 1"
            elif round["maxCombo"] == 14:
                query += ", \"14s\" = \"14s\" + 1"

            query += """, maxCombo = max(maxCombo, ?),
                    comboSum = comboSum + ?,
                    roundsPlayedStandard = roundsPlayedStandard + 1,
                    linesGot = linesGot + ?, 
                    linesSent = linesSent + ?,
                    linesBlocked = linesBlocked + ?,                
                    standardTime = standardTime + ?"""
            params += [round["maxCombo"], 
                    round["maxCombo"], 
                    round["linesGot"], 
                    round["linesSent"], 
                    round["linesBlocked"], 
                    round["playDuration"]]
        query += " where userId = ?"
        params.append(round["userId"])
        db.execute(query,params)
        count += 1
    log(f"Processed {count} rounds.")
    db.commit()
    return