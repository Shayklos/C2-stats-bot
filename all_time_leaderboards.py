from collections import OrderedDict
from pyexcel_ods3 import save_data
import sqlite3, json
from datetime import datetime, timedelta
from time import perf_counter
import os

db = sqlite3.connect("files/fullCultris.db")
# db.row_factory = sqlite3.Row
requiredMatches = 10

class Leaderboard():
    #Namespace for leaderboards
    
    def Average_BPM(db: sqlite3.Connection, roundID_from, roundID_to, requiredMatches = requiredMatches):
        cur = db.execute(
            """
            select name, 
                60.0 * sum(Rounds.blocks)/sum(playDuration) as avgBPM, 
                count(Rounds.roundId) as c, 
                Users.userId 
            from Rounds 
                    inner join Users on Users.userId = Rounds.userId 
                    inner join Matches on Matches.roundId = Rounds.roundId 
            where Matches.roundId between ? and ? and
                Users.userId is not null group by Users.userId having avgBPM > 0 and 
                c> ? order by avgBPM desc""", 
            (roundID_from, roundID_to, requiredMatches))
        bpm = cur.fetchall()

        return bpm
    Average_BPM.header = ["Name", "Average BPM", "Rounds played", "User ID"]

    def Power(db: sqlite3.Connection, roundID_from, roundID_to, requiredMatches = requiredMatches):
        powerTable = {2: 37.8883647435868, 3: 35.4831455255647, 4: 40.1465889629567, 5: 44.2602184213111, 6: 48.575338292518, 7: 50.649550305342, 8: 51.9969119509592, 9: 56.306414280463}
        def power(roomsize, opm):
            #without multiplying by 37.88... first. it'll be multiplied at the end (small optimization)
            if 1 < roomsize < 10:
                return opm/powerTable.get(roomsize)
            else:
                return opm/(3*roomsize + 29.4)

        PowerDict = dict()
        UsersDict = dict() #Might be worth to keep track of Userid-username via db
        rounds = db.execute("""
            select roomsize, 
                Users.userId,
                name, 
                60*(rounds.linesSent + rounds.linesBlocked)/playDuration as OPM 
                from Rounds join Users   on Rounds.UserId = Users.userId 
                            join Matches on Matches.roundId = Rounds.roundId 
                where ruleset = 0 and 
                    roomsize > 1 and
                    playDuration and 
                    Matches.roundId between ? and ?
    """, (roundID_from,roundID_to))
        
        for round in rounds:
            if round["OPM"] is None: #meaning playDuration is 0
                continue

            if PowerDict.get(round["userId"]):
                PowerDict[round["userId"]].append(power(round["roomsize"],round["OPM"]))
            else:
                PowerDict[round["userId"]] = [power(round["roomsize"],round["OPM"])]
                UsersDict[round["userId"]] = round["name"]


        return sorted([
            (UsersDict[player],
            powerTable.get(2)*sum(PowerDict[player])/len(PowerDict[player]),
            len(PowerDict[player]),
            player,
            )             
                for player in PowerDict if len(PowerDict[player]) > requiredMatches], 
            key=lambda x: x[1], reverse=True)
    Power.header = ["Name", "Power", "Rounds played", "User ID"]

    def Many(db: sqlite3.Connection, roundID_from, roundID_to, requiredMatches = requiredMatches):
        cur = db.execute(
            """
            select name, 
                sum(Rounds.linesSent) as Sent,
                60.0 * sum(Rounds.blocks)/sum(playDuration) as avgBPM, 
                60.0 * sum(Rounds.linesSent + Rounds.linesBlocked)/sum(playDuration) as avgOPM, 
                100.0*sum(Rounds.linesSent + Rounds.linesBlocked)/sum(blocks) as avgOPB,
                60.0 * sum(Rounds.linesSent)/sum(playDuration) as avgSPM, 
                100.0*sum(Rounds.linesBlocked)/sum(Rounds.linesGot) as blocked_percent,
                sum(playDuration) / 3600.0 as hours,
                max(Rounds.maxCombo) as maxCombo,
                1.0*sum(Rounds.maxCombo)/count(Matches.roundId) as avgMaxCombo,
                count(Rounds.roundId) as c, 
                Users.userId 
            from Rounds 
                    inner join Users on Users.userId = Rounds.userId 
                    inner join Matches on Matches.roundId = Rounds.roundId 
            where Matches.roundId between ? and ? and
                Users.userId is not null group by Users.userId having avgBPM > 0 and 
                c> ? order by avgBPM desc""", 
            (roundID_from, roundID_to, requiredMatches))
        bpm = cur.fetchall()

        return bpm
    Many.header = ["Name", "Sent", "BPM", "OPM", "OPB", "SPM", "Blocked%", "Hours played", "Max Combo", "Average max combo", "Rounds played", "UserID"]
def get_ids(starting_from = datetime(2011, 1, 1), stop_at = datetime(2023, 1, 1)):
    dates = dict()
    id = 0

    date = starting_from
    while date < stop_at:
        id = id if id else 0
        id = db.execute("select max(roundId) from Matches where start < ? and roundId < (? + 50000) ", (date, id)).fetchone()[0]
        dates[f"{date.year}-{date.month}-{date.day}"] = id
        date += timedelta(days = 7)
        
        #if days + 7 in another year, adjust to take a bit more than a week
        if (date + timedelta(days = 7)).year != date.year:
             date = datetime(date.year + 1, 1, 1)
        print(date)

    with open("files/datesIDs.json", "a") as file:
            json.dump(dates,file)


def createODS(year, func, title, header = ["Name", "Stat", "Rounds played", "User ID"]):
    with open("files/datesIDs.json", "r") as file:
        all_dates : dict = json.load(file)
    

    dates = []
    for date in all_dates.keys():
        if date[:4] == str(year):
            dates.append(date)
            continue 

        if date[:4] == str(year+1):
            dates.append(date)
            break

    next_dates = iter(dates)
    next(next_dates)

    data = OrderedDict()
    counter = 0 
    for date1, date2 in zip(dates, next_dates):
        print(all_dates[date1], all_dates[date2])
        # print({date1 : [header] + func(db, all_dates[date1]+1, all_dates[date2])})
        # point_data = ['None' if row is None else row for row in func(db, all_dates[date1]+1, all_dates[date2])]
        point_data = [['None' if element is None else element for element in row] for row in func(db, all_dates[date1]+1, all_dates[date2])]
        # print(point_data)
        data.update({date1 : [header] + point_data})
    
    directory = f"files/extra/all-time leaderboards/{year}/"
    if not os.path.exists(directory):
        os.makedirs(directory)
    # print(data)
    save_data(directory + f"{title}.ods", data)


years = [
         2011, 
        #  2012, 
        #  2013, 
        #  2014, 
        #  2015, 
        #  2016, 
        #  2017, 
        #  2018, 
        #  2019, 
        #  2020, 
        #  2021, 
        #  2022
         ]

stats = [
    # ["Average BPM", Leaderboard.Average_BPM, Leaderboard.Average_BPM.header],     
    ["Many", Leaderboard.Many, Leaderboard.Many.header]
]



if __name__ == '__main__':
    for year in years:
        for stat_function, stat, header in stats:
            createODS(year, stat, stat_function, header)