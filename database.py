import sqlite3, urllib.request, json
from constants import * 
from datetime import datetime,timedelta
from pytz import timezone
from logger import *
from concurrent.futures import ThreadPoolExecutor
from thefuzz import fuzz
from time import sleep
from methods import *


    

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

            query1 = "insert into Matches values (?, ?, ?, ?, ?)"
            query2 = "insert into Rounds values (?,?,?,?,?,?,?,?,?,?,?)"
            parameters1, parameters2 = [], []
            for round in data:
                round_param1 = (
                    round.get("roundId"), 
                    datetime.strptime(round.get('start').split('.')[0], timeformat), #ignoring ms
                    round.get("ruleset"), 
                    round.get("speedLimit"),
                    round.get("isOfficial")
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
                    player.get("cheeseRows"),
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
        log(f"in add_profile_data: Couldn't add {userId}.", 'files/log_error.txt')
        return
    
    if data.get("stats") is None:
        query = "update Users set name = ? where userId = ?"
        params = (data.get("name"), userId)
    else:
        res = db.execute("select peakRank, peakRankScore from Users where userId = ?", (userId,))
        old_rank_data = res.fetchone() #320.0, 8
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

# add_profile_data(db, 5840)

@log_time
def add_recent_profile_data(db, days=7, add_to_netscores=False, commit = False):
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
        add_profile_data(db, id[0], add_to_netscores=add_to_netscores, commit=commit)
    

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

    date_now = datetime.now(tz = timezone('UTC'))
    date = date_now-timedelta(days=days)

    res = db.execute("select max(maxCombo), max(blocks/playDuration)*60 from Rounds inner join Matches on Rounds.roundId = Matches.roundId where playDuration > 10.5 and userId = ? and start > ?",
                     (userId,date))
    bestCombo, bestBPM = res.fetchone()

    res = db.execute("""select 
                60*sum(linesSent)/sum(playDuration) as avgSPM, 
                100*cast(sum(linesBlocked) as float)/sum(linesGot) as blockedpercent,
                cast(sum(maxCombo) as float)/count(Matches.roundId) as avgCombo,
                100*cast((sum(linesSent)+sum(linesBlocked)) as float) / sum(blocks) as outputperpiece,
				60*cast((sum(linesSent)+sum(linesBlocked)) as float) / sum(playDuration) as outputperminute
                from Matches inner join (select * from rounds where userId = ?) as s on Matches.roundId = s.roundId where ruleset = 0 and start > ?
                
                """, (userId,date))
    (avgSPM, blockedpercent, avgCombo, outputperpiece, outputperminute) = res.fetchone()
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
                        select 100*cast(wins as float)/played, played as winrate from wins join played
						
                """, (date, date, userId, userId))
    (winrate, played) = res.fetchone()
    return{ 
        "avgBPM" : avgBPM, 
        "avgCombo" : avgCombo, 
        "avgSPM" : avgSPM, 
        "blockedpercent" : blockedpercent, 
        "outputperpiece" :  outputperpiece, 
        "outputperminute" : outputperminute,
        "mins" : mins, 
        "winrate" : winrate,
        "played" : played,
        "bestCombo" : bestCombo,
        "bestBPM" : bestBPM,
    }
# print(time_based_stats(db, 5840))

def weekly_best(db, days = 7):
    date_now = datetime.now(tz = timezone('UTC'))
    res = db.execute("""
        with recentRounds as (select Matches.roundId, linesSent, playDuration, userId from Rounds inner join Matches on Rounds.roundId = Matches.roundId where start > ?)
            select name, 60*recentRounds.linesSent/playDuration as SPM from recentRounds inner join Users on recentRounds.userId = Users.userId order by SPM desc limit 5
        """, (date_now-timedelta(days=days),) )
    
    top5SPM = res.fetchall()
    
    res = db.execute("""
        select name, playDuration from Rounds join Matches on Rounds.roundId = Matches.roundId join Users on users.userId = Rounds.userId 
        where blocks>8 and rounds.maxCombo> 2 and ruleset = 1 and start > ? and not cheeseRows order by playDuration asc limit 5                                
                     """, (date_now-timedelta(days=days),) )
    
    top5Cheese = res.fetchall()

    return (top5SPM, top5Cheese)


def getNetscore(db, userId = None, username = None):
    """
    DOES NOT return a Netscore. Returns the oldest rank score stored of a player, and the days this data has
    """
    if not (userId or username):
        return None
    if username and not userId:
        userId = find_userId(db, username)
        if userId is None:
            return None
        
    scores = db.execute("select day1, day2, day3, day4, day5, day6, day7 from Netscores where userId = ?", (userId, )).fetchone()
    if scores is None:
        return 0, 0
    
    i = -1
    while not (oldest := scores[i]):
        i-=1

    return oldest, 8+i



def getNetscores(db, days = 7, aproximation = True):
    """
    Intended to be the list of netscores to send to /netscores in bot.py
    """

    return db.execute(
        f"""with elegibleUsers as (select distinct userId as u from Rounds 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ?)
        select Users.userId, name, day1-day{days} as net from Netscores inner join Users on Netscores.userId = Users.userId inner join elegibleUsers on u=Users.userId where day{days} is not null order by net desc
        """, 
        (datetime.now(tz = timezone('UTC'))-timedelta(days=days),)).fetchall()
    


    

def getCombos(db, days = 7, requiredMatches = 15):
    combos = db.execute(f"""select Rounds.userId, name, cast(sum(Rounds.maxCombo) as float)/count(Matches.roundId) as avgCombo, count(Matches.roundId) as c
                from Matches inner join Rounds on Matches.roundId = Rounds.roundId inner join users on users.userId = rounds.userId where ruleset = 0 and start > ? group by Rounds.userId having c>{requiredMatches} order by avgCombo desc """,
                (datetime.now(tz = timezone('UTC'))-timedelta(days=days),)).fetchall()
    
    return [(combo[0], combo[1], f"**{combo[2]:.2f}** in {combo[3]} matches" ) for combo in combos ]





def getPlayersOnline(db):
    with urllib.request.urlopen("https://gewaltig.net/") as URL:
        webdata = str(URL.read())
    start = webdata.find("Currently Playing")
    end = webdata[start:].find("<p>")
    ids = [int(id[:id.find('\"')]) for id in webdata[start:start+end].split("ProfileView/")[1:]]
    
    r = db.execute("select name from Users where userId in (%s)" % ','.join('?'*len(ids)), ids).fetchall()
    return [r[i][0] for i in range(len(r))]


def fuzzysearch(db, username: str) -> tuple:
    users = db.execute("select userId, name from Users where name is not ''").fetchall()
    ratios = sorted([(fuzz.ratio(username.lower(), user[1].lower()), user[0], user[1]) for user in users], reverse=True)

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
    

@log_time
def update_ranks(db, old_round, new_round, commit = False):

    if old_round>new_round:
        log("0 places changed in the leaderboard")
        return
    res = db.execute("""select userId, rank from Users inner join
(select distinct userid as u from rounds inner join Matches on Matches.roundId = Rounds.roundId and u
                     where ruleset = 0 and isOfficial and speedLimit <> 80 and Rounds.roundid between ? and ?)
on userId = u
""", (old_round, new_round)).fetchall()
    
    if not res:
        log("0 places changed in the leaderboard")
        return
    #Creating the changes array, that speciefies exactly how are ranks swapped
    #example changes = [(39, 40), (18, 18), (113, 138), (11793, 11801)]
    #means rank 39 goes to rank 40, rank 18 stays the same, rank 113 goes to rank 138... 
    changes = []
    for id, rank in res:
        url = BASE_USER_URL+str(id)
        try:
            with urllib.request.urlopen(url) as URL:
                data = json.load(URL)
        except urllib.error.HTTPError:
            # website is down at the moment
            log(f"in update_ranks: Couldn't add {id}. old_round: {old_round}; new_round:{old_round}. Manually call this function with given old_round, newest round?", "files/log_error.txt")
            return

        if data.get("stats") is None:
            query = "update Users set name = ? where userId = ?"
            params = (data.get("name"), id)
            log(f"Couldn't add {id . old_round: {old_round}}. Weird rank")
            continue
        else:
            res = db.execute("select peakRank, peakRankScore from Users where userId = ?", (id,))
            old_rank_data = res.fetchone() #320.0, 8
            # print(old_rank_data)
            stats = data.get("stats")
            query = """update Users 
                        set name = ?,
                            
                            score = ?,
                            maxCombo = ?,
                            playedRounds = ?,
                            wins = ?,
                            maxBPM = ?,
                            avgBPM = ?,
                            playedMin = ?
            """
            params = [stats.get("name"),
                    # stats.get("rank"),
                    stats.get("score"),
                    stats.get("maxCombo"),
                    stats.get("playedRounds"),
                    stats.get("wins"),
                    stats.get("maxroundBpm"),
                    stats.get("avgroundBpm"),
                    stats.get("playedmin")]
            
            query += ", peakRank = ?, peakRankScore = ? where userId = ?"
            if old_rank_data[0] is None:
                params += [stats.get("rank"), stats.get("score"), id]
            else:
                # print(stats.get("rank"), stats.get("score"))
                params += [min(stats.get("rank"), old_rank_data[0]), max(stats.get("score"), old_rank_data[1]), id]    
        db.execute(query,params)
        db.commit()
        sleep(0.1) #releases database lock for a moment
        log(f"Added {params[0]}")
        changes.append((rank, stats.get("rank")))

    #Select range of users to change (for performance, works with the whole leaderboard)
    MIN = min([min(a, b) for a, b in changes])
    MAX = max([max(a, b) for a, b in changes])

    players = db.execute("select userId, rank from Users where rank between ? and ? order by rank",
                     (MIN, MAX)).fetchall()
    offset = players[0][1] # = MIN
    result = [None]*len(players)
    for change in sorted(changes, reverse=True):
        result[change[1]-offset] = (change[1] ,players[change[0]-offset][0])
        del players[change[0]-offset]
    for i in range(len(result)):
        if not result[i]:
            result[i] = (i+offset,players[0][0])
            del players[0]

    #finally, update new ranks
    for rank, id in result:
        db.execute("update Users set rank = ? where userId = ?", (rank,id))

    log(f"{len(changes)} places changed in the leaderboard")
    if commit:
        db.commit()


def getRankings(db, start = 1, end = 20, fast = True):
    if start > 0:
        if fast:
            res = db.execute("select userId, name, score from Users where rank between ? and ? order by rank asc", (start, end)).fetchall()
            return [(a[0], a[1], str(round(a[2],1))) for a in res]

        else:
            res = db.execute("select userId, name from Users where rank between ? and ? order by rank asc", (start, end)).fetchall()
            leaderboard = []
            for userId, name in res:
                url = BASE_USER_URL+str(userId)
                try:
                    with urllib.request.urlopen(url) as URL:
                        data = json.load(URL)
                except urllib.error.HTTPError:
                    score = db.execute("select score from Users where userId = ?", (userId,)).fetchone()[0]
                    log(f"In getRankings: Couldn't display {userId} in leaderboard.", file = 'files/log_error.txt')
                    leaderboard.append((userId, name, f"~{score:.2f}"))
                leaderboard.append((userId, name, f"{data.get('stats').get('score'):.1f}"))
            return leaderboard
    else: #really don't care enough sorry for these next lines of code
        if fast:
            maxrank = db.execute("select max(rank) from Users").fetchone()[0]
            res = db.execute("select userId, name, score from Users where rank between ? and ? order by rank desc", ((maxrank-19) + 20*(start+1), maxrank + 20*(start+1))).fetchall()
            return [(a[0], a[1], str(round(a[2],1))) for a in res]
        else: 
            res = db.execute("select userId, name from Users where rank between ? and ? order by rank desc", ((maxrank-19) + 20*(start+1), maxrank + 20*(start+1))).fetchall()
            leaderboard = []
            for userId, name in res:
                url = BASE_USER_URL+str(userId)
                try:
                    with urllib.request.urlopen(url) as URL:
                        data = json.load(URL)
                except urllib.error.HTTPError:
                    score = db.execute("select score from Users where userId = ?", (userId,)).fetchone()[0]
                    log(f"Couldn't display {userId} in leaderboard.", "files/log_error.txt")
                    leaderboard.append((userId, name, f"~{score:.2f}"))
                leaderboard.append((userId, name, f"{data.get('stats').get('score'):.1f}"))
            return leaderboard



def getSent(db, days = 7):
    date_now = datetime.now(tz = timezone('UTC'))
    sent = db.execute(
        """select Users.userId, name, sum(Rounds.linesSent) as Sent from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null group by Users.userId having Sent > 0 order by Sent desc""", 
        (date_now-timedelta(days=days),)).fetchall()
    
    return [(combo[0], combo[1], f"{thousandsSeparator(combo[2])}") for combo in sent ]

def getavgSPM(db, days = 7, requiredMatches = 40):
    date_now = datetime.now(tz = timezone('UTC'))
    spm = db.execute(
        """select Users.userId, name, round(60*cast(sum(Rounds.linesSent) as float)/sum(playDuration),1) as avgSPM, count(Rounds.roundId) as c from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null and ruleset = 0 group by Users.userId having avgSPM > 0 and c> ? order by avgSPM desc""", 
        (date_now-timedelta(days=days),requiredMatches)).fetchall()


    return [(combo[0], combo[1], f"**{combo[2]}** in {combo[3]} matches" ) for combo in spm ]



def getavgBPM(db, days = 7, requiredMatches = 40):
    date_now = datetime.now(tz = timezone('UTC'))
    spm = db.execute(
        """select Users.userId, name, round(60*cast(sum(Rounds.blocks) as float)/sum(playDuration),1) as avgBPM, count(Rounds.roundId) as c from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null group by Users.userId having avgBPM > 0 and c> ? order by avgBPM desc""", 
        (date_now-timedelta(days=days),requiredMatches)).fetchall()


    return [(combo[0], combo[1], f"**{combo[2]}** in {combo[3]} matches" ) for combo in spm ]


def getBlockedPercent(db, days = 7, requiredMatches = 40):
    date_now = datetime.now(tz = timezone('UTC'))
    spm = db.execute(
        """select Users.userId, name, round(100*cast(sum(Rounds.linesBlocked) as float)/sum(Rounds.linesGot),1) as avgSPM, count(Rounds.roundId) as c from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null and ruleset = 0 group by Users.userId having avgSPM > 0 and c> ? order by avgSPM desc""", 
        (date_now-timedelta(days=days),requiredMatches)).fetchall()


    return [(combo[0], combo[1], f"**{combo[2]}%** in {combo[3]} matches" ) for combo in spm ]


if __name__ == "__main__":
    db = sqlite3.connect(r"files\cultris.db")
    # print(getBlockedPercent(db)) 
    
# print(getSent(db))

# print(getRankings(db, -2))

# print(getNetscores(db))
# print(fuzzysearch(db, 'chay'))
# print(fuzz.ratio("z2sam", 'z2sam'))

# add_profile_data(db, 14331, add_to_netscores=False, commit=True)
    # add_recent_profile_data(db, add_to_netscores=True)
    # db.commit()
# print(player_stats(db, "[DEV] Simon"))
# print(time_based_stats(db, username="Shay"))
# print(weeklyBest(db))

