import sqlite3
import urllib.request, json
from constants import * 
from datetime import datetime,timedelta
from pytz import timezone
from logger import *
from concurrent.futures import ThreadPoolExecutor
from thefuzz import fuzz

#TODO check if any queries break when userId or similar is null

db = sqlite3.connect(r"files\cultris.db")

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

    # db = sqlite3.connect(r"files\cultris.db")
    res = db.execute("select max(roundId) from Matches where start < (?)", (date_now-timedelta(days=days),))
    id = res.fetchone()[0]

    res = db.execute("select count(roundId) from Matches where roundId < (?)", (id,))
    db.execute("delete from Matches where roundId < (?)", (id,))
    db.execute("delete from Rounds where roundId < (?)", (id,))
    log(f"Deleted {res.fetchone()[0]} matches.")
    db.commit()


@log_time
def process_data(db, oldRound, newRound):
    """
    Takes all the rounds between oldRound and newRound. Adds data to the database.

    rounds element example
    ["roundId","userId","name","got","sent","blocked","blocks", "maxCombo", "playDuration", "team"]
    (12421684,  None,   'guest', 25,    47,     14,       78,         10,        39.1243,      None), 
    """
    def player_dict_one(player_rounds):
        """
        Transforms list into dictionary.
        Used in process_data for clarity.
        """
        #TODO remove roundId
        conversion_table = ["roundId", "userId", "guestName", "linesGot", "linesSent", "linesBlocked", "blocks", "maxCombo", "playDuration", "team"]
        return {conversion_table[i] : player_rounds[i] for i in range(len(conversion_table))} 

    rounds = db.execute("select * from rounds where roundId between ? and ?", (oldRound, newRound))
    rulesets = db.execute("select ruleset from matches where roundId between ? and ?", (oldRound, newRound))
    

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

            #TODO updating maxCombo might be unnecesary as it is already part of the user profile
            query += """, maxCombo = max(maxCombo, ?),
                    comboSum = comboSum + ?,
                    playedRoundsStandard = playedRoundsStandard + 1,
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


def find_userId(db, username: str):
    """
    Takes an username e.g. Shay and returns their user id e.g. 5840
    Returns None if no player with that id exists in db 
    """

    res = db.execute("select userId from Users where name = ?", (username,)).fetchone()

    if res is None:
        return None    
    return res[0]


def add_profile_data(db, userId, add_to_netscores = False, commit = False):
    """
    Adds/updates to db data found in user profiles (maxCombo, avgBPM, maxBPM, etc)
    """
    if type(userId) != str:
        userId = str(userId)

    url = BASE_USER_URL+userId
    try:
        with urllib.request.urlopen(url) as URL:
            data = json.load(URL)
    except urllib.error.HTTPError:
        # website is down at the moment
        log(f"couldn't add {userId}")
        pass
    
    if data.get("stats") is None:
        query = "update Users set name = ? where userId = ?"
        params = (data.get("name"), userId)
    else:
        res = db.execute("select peakRank, score from Users where userId = ?", (userId,))
        old_rank_data = res.fetchone()
        stats = data.get("stats")
        query = """update Users 
                    set name = ?,
                        rank = ?,
                        score = ?,
                        maxCombo = ?,
                        playedRounds = ?,
                        wins = ?,
                        maxBPM = ?,
                        avgBPM = ?,
                        playedMin = ?
        """
        params = [stats.get("name"),
                  stats.get("rank"),
                  stats.get("score"),
                  stats.get("maxCombo"),
                  stats.get("playedRounds"),
                  stats.get("wins"),
                  stats.get("maxroundBpm"),
                  stats.get("avgroundBpm"),
                  stats.get("playedmin")]
        if add_to_netscores:
            add_netscore(db, userId, stats.get("score"))


        query += ", peakRank = ?, peakRankScore = ? where userId = ?"
        if old_rank_data[0] is None:
            params += [stats.get("rank"), stats.get("score"), userId]
        else:
            params += [min(stats.get("rank"), old_rank_data[0]), max(stats.get("score"), old_rank_data[1]), userId]    
    db.execute(query,params)
    log(f"Added {params[0]}")
    if commit:
        db.commit()

    return data.get("gravatarHash")


# @log_time
def add_recent_profile_data(db, days=7, add_to_netscores=False):
    """
    Adds to the db data profiles of all players that have played in 'days' days
    """
    date_now = datetime.now(tz = timezone('UTC'))
    res = db.execute(
        "select distinct(userId) from Rounds Inner Join Matches on Rounds.roundId = Matches.roundId where start > ? and userId is not null", 
        (date_now-timedelta(days=days),))
    
    # with ThreadPoolExecutor(max_workers=1) as executor:
    #     futures = [executor.submit(function, x) for x in range(10)]
    while id := res.fetchone():
        add_profile_data(db, id[0], add_to_netscores=add_to_netscores, commit=False)
    

def add_netscore(db, userId, score):
    def push(List):
        # print(userId, score)
        # print(List)
        x = list(List)
        x.insert(0,score)
        return x[:-1]

    # print(userId)
    res = db.execute("select day1,day2,day3,day4,day5,day6,day7 from Netscores where userId = ?", (userId,))
    row = res.fetchone()
    # print(row)
    if row is None:
        db.execute("insert into Netscores (userId, day1) values (?, ?)", (userId, score))
        return

    db.execute("""update Netscores set
               day1=?,
               day2=?,
               day3=?,
               day4=?,
               day5=?,
               day6=?,
               day7=?
                where userId = ? 
               """,push(row) + [userId] )    


def update_userlist(db):
    res = db.execute("select max(userId) from Users")
    id = res.fetchone()[0]+1
   
    #TODO this is like uber bad practice, basically waiting for error connecting with the api to determine no more users left to add
    while True:
        url = BASE_USER_URL+str(id)
        try:
            with urllib.request.urlopen(url) as URL:
                data = json.load(URL)

                if data.get("stats") is None:
                    query = "insert into Users (name, userId) values (?, ?)"
                    params = (data.get("name"), id)
                else:
                    stats = data.get("stats")
                    query = """insert into Users (userId, name, rank, score, maxCombo, playedRounds, wins, maxBPM, avgBPM, playedMin) 
                    values (?,?,?,?,?,?,?,?,?,?)                             
                    """
                    params = [id,
                            stats.get("name"),
                            stats.get("rank"),
                            stats.get("score"),
                            stats.get("maxCombo"),
                            stats.get("playedRounds"),
                            stats.get("wins"),
                            stats.get("maxroundBpm"),
                            stats.get("avgroundBpm"),
                            stats.get("playedmin")]
                # print(query,params)
                db.execute(query,params)
                log(f"Added user {id}.")
                id+=1

        except urllib.error.HTTPError:
            # website is down at the moment
            return
    

def player_stats(db, userId = None, username = None):
    if not (userId or username):
        return None
    if username and not userId:
        userId = find_userId(db, username)
        if userId is None:
            return None
    hash = add_profile_data(db, userId, commit=True)
    res = db.execute("select * from Users where userId = ?", (userId,))
    data = res.fetchone()
    return {
        "userId" : data[0],
        "name" : data[1],
        "rank" : data[2],
        "score" : data[3],
        "maxCombo" : data[4],
        "playedRounds" : data[5],
        "playedRoundsStandard" : data[6],
        "wins" : data[7],
        "maxBPM" : data[8],
        "avgBPM" : data[9],
        "linesGot" : data[10],
        "linesSent" : data[11],
        "linesBlocked" : data[12],
        "blocksPlaced" : data[13],
        "14s" : data[14],
        "13s" : data[15],
        "12s" : data[16],
        "11s" : data[17],
        "10s" : data[18],
        "peakRank" : data[19],
        "peakRankScore" : data[20],
        "comboSum" : data[21],
        "teamsTime" : data[22],
        "cheeseTime" : data[23],
        "standardTime" : data[24],
        "playedMin" : data[25],
        "gravatarHash" : hash
    }


def time_based_stats(db, userId = None, username = None, days = 7):
    if not (userId or username):
        return None
    if username and not userId:
        userId = find_userId(db, username)
        if userId is None:
            return None
    #TODO change time period from lenght of db to 7 days

    date_now = datetime.now(tz = timezone('UTC'))
    date = date_now-timedelta(days=days)
    res = db.execute("""select 
                60*sum(linesSent)/sum(playDuration) as avgSPM, 
                100*cast(sum(linesBlocked) as float)/sum(linesGot) as blockedpercent,
                cast(sum(maxCombo) as float)/count(Matches.roundId) as avgCombo
                from Matches inner join (select * from rounds where userId = ?) as s on Matches.roundId = s.roundId where ruleset = 0 and start > ?
                
                """, (userId,date))
    (avgSPM, blockedpercent, avgCombo) = res.fetchone()
    res = db.execute("""select 
                    60*sum(blocks)/sum(playDuration) as avgBPM, 
                    sum(playDuration)/60 as mins
                    from Matches inner join (select * from rounds where userId = ?) as s on Matches.roundId = s.roundId and start > ?
                """, (userId,date))
    (avgBPM, mins) = res.fetchone()
    res = db.execute("""with roundIdWithWinner as (
                                select distinct(Rounds.roundId) as X, userId from Rounds inner join Matches on Rounds.roundId = Matches.roundId where start > ? GROUP by Rounds.roundId), 
	roundsWhereMoreThanOnePersonPlayed as (
                                select r from (select Rounds.roundId as r, count(Rounds.roundId) as c from rounds inner join Matches on Rounds.roundId = Matches.roundId where start > ? group by Rounds.roundId) where c>1),
	Wins as (
                                select count(X) as wins from roundIdWithWinner inner join roundsWhereMoreThanOnePersonPlayed on
                                    X = r where userId = ?),
	Played as (
                                select count(Rounds.roundId) as played
                            from roundsWhereMoreThanOnePersonPlayed inner join Rounds on Rounds.roundId = r where Rounds.userId = ?)
                        select 100*cast(wins as float)/played as winrate from wins join played
						
                """, (date, date, userId, userId))
    winrate = res.fetchone()[0]
    return{ 
        "avgBPM" : avgBPM, 
        "avgCombo" : avgCombo, 
        "avgSPM" : avgSPM, 
        "blockedpercent" : blockedpercent, 
        "mins" : mins, 
        "winrate" : winrate
    }
print(time_based_stats(db, 5840))

def weekly_best(db, days = 7):
    date_now = datetime.now(tz = timezone('UTC'))
    res = db.execute("""
        with recentRounds as (select Matches.roundId, linesSent, playDuration, userId from Rounds inner join Matches on Rounds.roundId = Matches.roundId where start > ?)
            select name, 60*recentRounds.linesSent/playDuration as SPM from recentRounds inner join Users on recentRounds.userId = Users.userId order by SPM desc limit 5
        """, (date_now-timedelta(days=days),) )
    
    top5SPM = res.fetchall()
    
    res = db.execute("""
        with top5Cheese as (
            with roundIdWithWinner as (
                        select distinct(roundId) as X, userId, playDuration, blocks, maxCombo from Rounds where blocks > 8 and maxCombo>5 GROUP by roundId), 
                roundsWhereMoreThanOnePersonPlayed as (
                        select r from (select roundId as r, count(roundId) as c from rounds group by roundId) where c>1)
                        
            select userId, playDuration from roundIdWithWinner inner join roundsWhereMoreThanOnePersonPlayed on X = r inner join Matches on Matches.roundId = r where ruleset = 1 and start > ? order by playDuration
            limit 5)
            select name, playDuration from top5Cheese inner join Users on Users.userId = top5Cheese.userId
                                """, (date_now-timedelta(days=days),) )
    
    top5Cheese = res.fetchall()

    return (top5SPM, top5Cheese)


def getNetscore(db, userId = None, username = None, aproximation = True, commit = False):
    if not (userId or username):
        return None
    if username and not userId:
        userId = find_userId(db, username)
        if userId is None:
            return None
    scores = db.execute("select day1, day2, day3, day4, day5, day6, day7 from Netscores where userId = ?", (userId, )).fetchone()
    if scores is None:
        return 0
    
    i = -1
    while not (oldest := scores[i]):
        i-=1

    if aproximation:
        print(scores, oldest)
        return scores[0]-oldest, -i
    
    add_profile_data(db, userId = userId, commit=commit)
    current_score = db.execute("select score from Users where userId = ?", (userId, )).fetchone()[0]
    return current_score-oldest, i


def getNetscores(db, days = 7, aproximation = True):
    date_now = datetime.now(tz = timezone('UTC'))
    ids = db.execute(
        """select distinct userId from Rounds 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and userId is not null order by userId asc""", 
        (date_now-timedelta(days=days),)).fetchall()
    
    for id in ids:
        print(id)
        scores = db.execute("select day1, day2, day3, day4, day5, day6, day7 from Netscores where userId = ?", id).fetchone()
        if scores is None:
            pass
        
        i = -1
        while not (oldest := scores[i]):
            break
        print(oldest)

    



def getPlayersOnline(db):
    with urllib.request.urlopen("https://gewaltig.net/") as URL:
        webdata = str(URL.read())
    start = webdata.find("Currently Playing")
    end = webdata[start:].find("<p>")
    ids = [int(id[:id.find('\"')]) for id in webdata[start:start+end].split("ProfileView/")[1:]]
    
    r = db.execute("select name from Users where userId in (%s)" % ','.join('?'*len(ids)), ids).fetchall()
    return [r[i][0] for i in range(len(r))]


def fuzzysearch(db, username: str):
    users = db.execute("select userId, name from Users where name is not ''").fetchall()
    start = time.perf_counter() 
    ratios = sorted([(fuzz.ratio(username, user[1]), user[0], user[1]) for user in users], reverse=True)
    end = time.perf_counter()
    print(end-start)

    return ratios[0]


def activePlayers(db, days = 7):
    date_now = datetime.now(tz = timezone('UTC'))
    res = db.execute(
        """select Users.userId, name, sum(playDuration) as mins from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null group by Users.userId order by mins desc""", 
        (date_now-timedelta(days=days),))
    return res.fetchall()
    

# print(getNetscores(db))
# print(fuzzysearch(db, 'chay'))
# print(fuzz.ratio("z2sam", 'z2sam'))

# add_profile_data(db, 14331, add_to_netscores=False, commit=True)
# add_recent_profile_data(db, add_to_netscores=True)
# db.commit()
# print(player_stats(db, "[DEV] Simon"))
# print(time_based_stats(db, username="Shay"))
# print(weeklyBest(db))
