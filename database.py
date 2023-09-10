import sqlite3, aiosqlite, asyncio, urllib.request, json
from settings import * 
from datetime import datetime,timedelta
from pytz import timezone
from logger import *
from thefuzz import fuzz
from time import sleep
from methods import *



async def newest_round(db: aiosqlite.Connection):
    res = await db.execute("select max(roundId) from Matches")
    result = await res.fetchone()
    return result[0]


@async_log_time
async def add_new_rounds(db: aiosqlite.Connection):
    """
    Adds to the database rounds played that are not already there.
    Relies on having data already.
    """
    first_round = await newest_round(db)+1 #First round that it is not in the db
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

            query1 = "insert into Matches values (?, ?, ?, ?, ?, ?)"
            query2 = "insert into Rounds values (?,?,?,?,?,?,?,?,?,?,?,?)"
            parameters1, parameters2 = [], []
            for round in data:
                round_param1 = (
                    round.get("roundId"), 
                    datetime.strptime(round.get('start')[:-1].split('.')[0], timeformat), #ignoring ms
                    round.get("ruleset"), 
                    len(round.get("players")), #roomsize
                    round.get("speedLimit"),
                    round.get("isOfficial")
                )
                parameters1.append(round_param1)
                
                players = round.get("players")
                place = 1
                for player in players:
                    params2 = (round.get("roundId"),
                    player.get("userId"),
                    player.get("guestName"),
                    place,
                    player.get("linesGot"),
                    player.get("linesSent"),
                    player.get("linesBlocked"),
                    player.get("blocks"),
                    player.get("maxCombo"),
                    player.get("playDuration"),
                    player.get("team"),
                    player.get("cheeseRows"),
                    )
                    place += 1
                    parameters2.append(params2)
                
                count += 1
                    
            await db.executemany(query1,parameters1)
            await db.executemany(query2,parameters2)
            roundN += 1000
        except Exception as e:
            print(e)
            roundN = await newest_round(db)+1
    
    log(f"Added {count} matches.")

    # #Returns new Rounds data (should probably separate this from the rest of the function)         
    # res = db.execute("select max(roundId) from Matches")
    # last_round = res.fetchone()[0]
    # db.execute("select * from")


@async_log_time
async def delete_old_data(db: aiosqlite.Connection, days=30):
    date_now = datetime.now(tz = timezone('UTC'))

    cur = await db.execute("select max(roundId) from Matches where start < (?)", (date_now-timedelta(days=days),))
    res = await cur.fetchone()
    id = res[0]

    res = await db.execute("select count(roundId) from Matches where roundId < (?)", (id,))
    count = await res.fetchone()
    await db.execute("delete from Matches where roundId < (?)", (id,))
    await db.execute("delete from Rounds where roundId < (?)", (id,))
    log(f"Deleted {count[0]} matches.")
    await db.commit()


@async_log_time
async def process_data(db: aiosqlite.Connection, oldRound, newRound):
    """
    Takes all the rounds between oldRound and newRound. Adds data to the database.
    """

    rounds = await db.execute("select * from rounds where roundId between ? and ?", (oldRound, newRound))
    rulesets = await db.execute("select ruleset from matches where roundId between ? and ?", (oldRound, newRound))
    

    current_roundId = None
    count = 0
    async for round in rounds:
        if round is None:
            break
        elif round["roundId"] != current_roundId:
            current_roundId = round["roundId"]
            cur = await rulesets.fetchone()
            ruleset = cur[0]
        

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
        await db.execute(query,params)
        count += 1
    # log(f"Processed {count} rounds.")
    await db.commit()
    return


async def find_userId(db: aiosqlite.Connection, username: str):
    """
    Takes an username e.g. Shay and returns their user id e.g. 5840
    Returns None if no player with that id exists in db 
    """

    cur = await db.execute("select userId from Users where name = ?", (username,))
    userId = await cur.fetchone() 

    if userId is None:
        return None    
    return userId[0]


async def update_profile_data(db: aiosqlite.Connection, userId, add_to_netscores = False, commit = False):
    """
    Adds/updates to db data found in user profiles (maxCombo, avgBPM, maxBPM, etc)
    """
    if type(userId) != str:
        userId = str(userId)

    url = BASE_USER_URL+userId
    try:
        with urllib.request.urlopen(url) as URL:
            data = json.load(URL)
    except:
        # website is down at the moment
        log(f"in update_profile_data: Couldn't add {userId}.", 'files/log_error.txt')
        await asyncio.sleep(30)
        await update_profile_data(db, userId, add_to_netscores, commit)
        return
    
    if data.get("stats") is None:
        query = "update Users set name = ? where userId = ?"
        params = (data.get("name"), userId)
    else:
        cur = await db.execute("select peakRank, peakRankScore, name from Users where userId = ?", (userId,))
        res = await cur.fetchone()
        old_rank_data = (res[0], res[1]) #320.0, 8
        old_name = res[2]
        stats = data.get("stats")
        if stats.get("name") != old_name:
            log(f"ID: {userId}: {old_name} → {stats.get('name')}", "files/log_namechanges.txt")
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
            await add_netscore(db, userId, stats.get("score"))


        query += ", peakRank = ?, peakRankScore = ? where userId = ?"
        if old_rank_data[0] is None:
            params += [stats.get("rank"), stats.get("score"), userId]
        else:
            params += [min(stats.get("rank"), old_rank_data[0]), max(stats.get("score"), old_rank_data[1]), userId] 
    while True:
        try:
            await db.execute(query,params)
            if commit:
                await db.commit()
        except Exception as e:
            print(e)
            asyncio.sleep(1)
            continue
        else:
            log(f"Added {params[0]}")
            break
    
    return data

@async_log_time
async def add_recent_profile_data(db: aiosqlite.Connection, days=7, add_to_netscores=False, commit = False):
    """
    Adds to the db data profiles of all players that have played in 'days' days
    """
    date_now = datetime.now(tz = timezone('UTC'))   
    async with db.execute(
        """select distinct(userId) from 
                Rounds Inner Join Matches on Rounds.roundId = Matches.roundId 
            where isOfficial and 
                ruleset = 0 and 
                start > ? and 
                userId is not null""", 
        (date_now-timedelta(days=days),)) as cursor:
        async for id in cursor:
            await update_profile_data(db, id[0], add_to_netscores=add_to_netscores, commit=commit)

    

async def add_netscore(db: aiosqlite.Connection, userId, score):
    def push(List):
        x = list(List)
        x.insert(0,score)
        return x[:-1]

    res = await db.execute("select day1,day2,day3,day4,day5,day6,day7 from Netscores where userId = ?", (userId,))
    row = await res.fetchone()
    if row is None:
        await db.execute("insert into Netscores (userId, day1) values (?, ?)", (userId, score))
        return
    
    while True:
        try:
            await db.execute("""update Netscores set
               day1=?,
               day2=?,
               day3=?,
               day4=?,
               day5=?,
               day6=?,
               day7=?
                where userId = ? 
               """,push(row) + [userId] )    
        except Exception as e:
            print(e)
            await asyncio.sleep(1)
            continue
        else:
            break

    


async def update_userlist(db: aiosqlite.Connection):
    res = await db.execute("select max(userId) from Users")
    row = await res.fetchone()
    id = row[0] + 1
    #TODO this is like uber bad practice, basically waiting for error connecting with the api to determine no more users left to add
    #TODO more importantly there could be holes in the way, which could make the userlist never update
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
                await db.execute(query,params)
                log(f"New account: user {data.get('name')} ({id}).")
                id+=1

        except urllib.error.HTTPError:
            # no website
            return
        except: #I've seen urllib.error.URLError and http.client.RemoteDisconnected
            # website is down at the moment / client has no internet connection
            log("No connection", 'files/log_errors.txt')
            await asyncio.sleep(30)
            await update_userlist(db)
    

async def player_stats(db: aiosqlite.Connection, userId = None, username = None):
    if not (userId or username):
        return None
    if username and not userId:
        userId = await find_userId(db, username)
        if userId is None:
            return None
    profile_data = await update_profile_data(db, userId, commit=True)
    hash = profile_data.get("gravatarHash")
    res = await db.execute("select * from Users where userId = ?", (userId,))
    data = await res.fetchone()
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


def time_based_stats_old(db: aiosqlite.Connection, userId = None, username = None, days = 7):
    #deprecated
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

async def time_based_stats(db: aiosqlite.Connection, userId = None, username = None, days = 7):
    #Get user's ID if not given
    if not (userId or username):
        return None
    if username and not userId:
        userId = await find_userId(db, username)
        if userId is None:
            return None

    date = datetime.now(tz = timezone('UTC'))-timedelta(days=days)

    rounds = await db.execute("""
                        select 	
                            roomsize,
                            place == 1 as winner,
                            maxCombo,
                            blocks,
                            playDuration,
                            linesSent,
                            linesBlocked,
                            linesGot,
                            rounds.roundId
                        from 
                    Rounds join Matches 
                        on Rounds.roundId = Matches.roundId 
                           join (select roundId, userId as winner from Rounds group by roundId) x 
                        on x.roundId=Rounds.roundId 
                        
                        where start > ? and 
                              userId = ? and 
                              playDuration and 
                              ruleset = 0""", (date, userId))

    played = winned = bestBPM = bestCombo = comboSum = blocks = sent = blocked = got = playedTime = power = ppb = roomsize1 = powerb= 0
    spm = opm = 0
    max_power = 0 
    async for round in rounds:
        played += 1
        if round["roomsize"] == 1:
            roomsize1 += 1
            continue 

        if round["winner"]:
            winned +=1
        
        spm += 60 * round["linesSent"] / round["playDuration"]
        opm += 60 * (round["linesSent"]+round["linesBlocked"]) / round["playDuration"]

        bestCombo    = max(bestCombo, round["maxCombo"])
        bestBPM      = max(bestBPM, 60*round["blocks"]/round["playDuration"])
        comboSum    += round["maxCombo"]
        blocks      += round["blocks"]
        playedTime  += round["playDuration"]
        sent        += round["linesSent"]
        blocked     += round["linesBlocked"]
        got         += round["linesGot"]

        #Power formula: powerTable(2) * OPM / powerTable(roomsize)
        #PPB formula: powerTable(2) * OPM / powerTable(roomsize)
        #Notice that constants that can be factored out are inserted at the end
        if powerTable.get(round["roomsize"]):          
            power += (round["linesSent"] + round["linesBlocked"])/(round["playDuration"]*powerTable.get(round["roomsize"]))
            powerb += (round["linesSent"] + round["linesBlocked"])/powerTable.get(round["roomsize"])
            try:
                ppb += (round["linesSent"] + round["linesBlocked"]) /( round["blocks"] * powerTable.get(round["roomsize"]))
            except: #division by 0
                pass
        else:
            power += (round["linesSent"] + round["linesBlocked"])/(round["playDuration"]*(3*round["roomsize"] + 29.4))
            powerb += (round["linesSent"] + round["linesBlocked"])/(3*round["roomsize"] + 29.4)
            try:
                ppb += (round["linesSent"] + round["linesBlocked"]) / (round["blocks"] * (3*round["roomsize"] + 29.4))
            except: #division by 0
                pass
    
    playedTime /= 60 #minutes 

    
    try:
        return{
            "bpm" : blocks/playedTime , 
            "avgCombo" : comboSum/(played-roomsize1), 
            "spm" : sent/playedTime, 
            "blocked%" : 100*blocked/got, 
            "opb" :  100*(sent+blocked)/blocks, 
            "opm" : (sent+blocked)/playedTime,
            "mins" : playedTime, 
            "winrate" : 100*(winned-roomsize1)/(played-roomsize1),
            "played" : played,
            "bestCombo" : bestCombo,
            "bestBPM" : bestBPM,
            "power": powerTable.get(2) * 60 * power/(played-roomsize1),
            "powerb": powerTable.get(2) * powerb/playedTime,
            "ppb": 100 * powerTable.get(2) * ppb/(played-roomsize1),
            "aspm" : spm/(played-roomsize1),
            "aopm" : opm/(played-roomsize1)
        }
    except ZeroDivisionError: #Player has barely played
        return{
            "avgBPM" : 0 , 
            "avgCombo" : 0, 
            "avgSPM" : 0, 
            "blockedpercent" : 0, 
            "outputperpiece" :  0, 
            "outputperminute" : 0,
            "mins" : 0, 
            "winrate" : 0,
            "played" : 0,
            "bestCombo" : 0,
            "bestBPM" : 0,
            "power": 0,
            "powerperblock": 0
        }



async def weekly_best(db: aiosqlite.Connection, days = 7, top = 5):


    date_now = datetime.now(tz = timezone('UTC'))
    res = await db.execute("""
        with recentRounds as 
            (select Matches.roundId, linesSent, playDuration, userId from Rounds join Matches on Rounds.roundId = Matches.roundId where start > ?)
        select name, 60*recentRounds.linesSent/playDuration as SPM 
            from recentRounds join Users 
                on recentRounds.userId = Users.userId 
            order by SPM desc limit ?
        """, (date_now-timedelta(days=days), top) )
    top5SPM = await res.fetchall()
    
    # cheeseRows = 0 if player has finished a Cheese game, but also if he's gone AFK,
    # so additional filters are needed. It's faulty but is the best thing I could think of
    res = await db.execute("""
        select name, playDuration 
            from Rounds join Matches on 
                Rounds.roundId = Matches.roundId 
                    join Users on 
                users.userId = Rounds.userId 
            where blocks>8 and rounds.maxCombo> 2 and ruleset = 1 and start > ? and not cheeseRows order by playDuration asc limit ?                                
                     """, (date_now-timedelta(days=days), top) )
    
    top5Cheese = await res.fetchall()

    return (top5SPM, top5Cheese)


async def getNetscore(db: aiosqlite.Connection, userId = None, username = None, days = 7):
    """
    DOES NOT return a Netscore. Returns the oldest rank score stored of a player, and the days this data has
    """
    if not (userId or username):
        return None
    if username and not userId:
        userId = await find_userId(db, username)
        if userId is None:
            return None
    
    days = min(7, days)
    query = "select "
    for i in range(1, days):
        query += f"day{i}, "
    query += f"day{days} from Netscores where userId = ?"


    cur = await db.execute(query, (userId, ))
    scores = await cur.fetchone()
    if scores is None:
        return 0, 0
    
    i = -1
    while not (oldest := scores[i]):
        i-=1

    return oldest, days+1+i



async def getNetscores(db: aiosqlite.Connection, days = 7, aproximation = True):
    """
    Intended to be the list of netscores to send to /netscores in bot.py
    """

    cur = await db.execute(
        f"""with elegibleUsers as (select distinct userId as u from Rounds 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ?)
        select Users.userId, name, day1-day{days} as net from Netscores inner join Users on Netscores.userId = Users.userId inner join elegibleUsers on u=Users.userId where day{days} is not null order by net desc
        """, 
        (datetime.now(tz = timezone('UTC'))-timedelta(days=days),))
    
    res = await cur.fetchall()

    return res
    


    

async def getCombos(db: aiosqlite.Connection, days = 7, requiredMatches = requiredMatchesCombos, rawdata = False):
    if days == 1:
        requiredMatches //= 4
    elif days == 2:
        requiredMatches //=3

    cur = await db.execute(f"""select Rounds.userId, name, cast(sum(Rounds.maxCombo) as float)/count(Matches.roundId) as avgCombo, count(Matches.roundId) as c
                from Matches inner join Rounds on Matches.roundId = Rounds.roundId inner join users on users.userId = rounds.userId where ruleset = 0 and start > ? group by Rounds.userId having c>{requiredMatches} order by avgCombo desc """,
                (datetime.now(tz = timezone('UTC'))-timedelta(days=days),))
    combos = await cur.fetchall()
    if rawdata:
        return [(combo[0], combo[1], combo[2]) for combo in combos]
    else:
        return [(combo[0], combo[1], f"**{combo[2]:.2f}** in {combo[3]} matches" ) for combo in combos]





def getPlayersOnline():
    with urllib.request.urlopen(LIVEINFO_URL) as URL:
        liveinfo = json.load(URL)


    result = ""
    for room in liveinfo.get("rooms"):
        if room.get("players"):
            result += f"\n**{room.get('name')}**:\n"
            players = []
            for player in liveinfo.get("players"):
                if player.get("room") is room.get("id"): #Note that == doesn't work here, since False == 0 is True
                    players.append((player.get("currentscore"), player.get("name"), player.get("afk") ))
            players = sorted(players, reverse=True)
            for i, player in enumerate(players):
                if i==0:
                    if player[2]:
                        result += f"{player[0]}\u1CBC\u1CBC\u1CBC\u1CBC***{player[1]}***\n"
                    else:
                        result += f"{player[0]}\u1CBC\u1CBC\u1CBC\u1CBC**{player[1]}**\n"

                else:
                    if player[2]:
                        result += f"{player[0]}\u1CBC\u1CBC\u1CBC\u1CBC_{player[1]}_\n"
                    else:
                        result += f"{player[0]}\u1CBC\u1CBC\u1CBC\u1CBC{player[1]}\n"
    players = []
    for player in liveinfo.get("players"):
        if player.get("status")!="room":
            players.append((player.get('challenge'), player.get("name")))

    result+="\n"
    players=sorted(players)
    for player in players:
        if player[0]:
            result+= f"**{player[1]}**: Playing challenge \"{player[0]}\"\n"
        else:
            result+= f"**{player[1]}**: Hanging out in the lobby\n"
    return result
        


async def getPlayersWhoPlayedRecently(db: aiosqlite.Connection, hours=1):
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute("select distinct name from Rounds join Matches on Rounds.roundId = Matches.roundId join Users on Users.userId = Rounds.userId where start > ?", 
        (date_now-timedelta(hours=hours), ))
    players = await cur.fetchall()
    cur = await db.execute("select distinct guestName from Rounds join Matches on Rounds.roundId = Matches.roundId where guestName is not null and start>?", 
        (date_now-timedelta(hours=hours), ))
    guests = await cur.fetchall()

    return{
        "players": players,
        "guests": guests
    }

async def fuzzysearch(db: aiosqlite.Connection, username: str) -> tuple:
    cur = await db.execute("select userId, name from Users where name is not ''")
    users = await cur.fetchall()
    ratios = sorted([(fuzz.ratio(username.lower(), user[1].lower()), user[0], user[1]) for user in users], reverse=True)

    return ratios[0]



async def getTimePlayed(db: aiosqlite.Connection, days = 7):
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute(
        """select Users.userId, name, sum(playDuration) as mins from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null group by Users.userId order by mins desc""", 
        (date_now-timedelta(days=days),))
    
    res = await cur.fetchall()
    return res
    

@async_log_time
async def update_ranks(db: aiosqlite.Connection, old_round, new_round, commit = False):
    """
    Detects which persons have played on FFA since old_round and new_round, update
    """
    #TODO: remake this function, it sucks
    if old_round>new_round:
        log("0 places changed in the leaderboard")
        return
    cur = await db.execute("""select userId, rank from Users inner join
(select distinct userid as u from rounds inner join Matches on Matches.roundId = Rounds.roundId and u
                     where ruleset = 0 and isOfficial and speedLimit <> 80 and Rounds.roundid between ? and ?)
on userId = u
""", (old_round, new_round))
    
    res = await cur.fetchall()
    if not res:
        log("0 places changed in the leaderboard")
        return
    #Creating the changes array, that speciefies exactly how are ranks swapped
    #example changes = [(39, 40), (18, 18), (113, 138), (11793, 11801)]
    #means rank 39 goes to rank 40, rank 18 stays the same, rank 113 goes to rank 138... 
    changes = []
    NoneRanks = False
    for id, rank in res:
        url = BASE_USER_URL+str(id)
        try:
            with urllib.request.urlopen(url) as URL:
                data = json.load(URL)
        except:
            # website is down at the moment
            log(f"in update_ranks: Couldn't add {id}. old_round: {old_round}; new_round:{old_round}. Manually call this function with given old_round, newest round?", "files/log_error.txt")
            await asyncio.sleep(30)
            await update_ranks(db, old_round, new_round, commit)
            return

        if data.get("stats") is None:
            query = "update Users set name = ? where userId = ?"
            params = (data.get("name"), id)
            log(f"Couldn't add {id}. old_round: {old_round}. Weird rank")
            continue
        else:
            cur = await db.execute("select peakRank, peakRankScore, name from Users where userId = ?", (id,))
            peak = await cur.fetchone()
            old_rank_data = (peak[0], peak[1]) #320.0, 8
            old_name = peak[2]
            stats = data.get("stats")
            if stats.get("name") != old_name:
                log(f"ID: {id}: {old_name} → {stats.get('name')}", "files/log_namechanges.txt")
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
            if not old_rank_data[0]:
                params += [stats.get("rank"), stats.get("score"), id]
            else:
                # print(stats.get("rank"), stats.get("score"))
                params += [min(stats.get("rank"), old_rank_data[0]), max(stats.get("score"), old_rank_data[1]), id]    
        await db.execute(query,params)
        await db.commit()
        await asyncio.sleep(0) #releases database lock for a moment
        log(f"Updated {params[0]}")
        changes.append((rank, stats.get("rank")))
        if not rank:
            NoneRanks = True

    #New accounts will have a rank of None, so give them the highest possible rank for the purposes of this method
    if NoneRanks:
        cur = await db.execute("select max(rank) from Users")
        res = await cur.fetchone()
        maxround = res[0]+1
        for i, element in enumerate(changes):
            if element[0]:
                continue
            changes[i] = (maxround, element[1])
            maxround += 1

    #Select range of users to change (for performance, works with the whole leaderboard)
    MIN = min([min(a, b) for a, b in changes])
    MAX = max([max(a, b) for a, b in changes])

    cur = await db.execute("select userId, rank from Users where rank between ? and ? order by rank",
                     (MIN, MAX))
    players = await cur.fetchall()
    offset = players[0][1] # = MIN
    result = [None]*len(players)

    try:
        for change in sorted(changes, reverse=True):
            result[change[1]-offset] = (change[1] ,players[change[0]-offset][0]) 
            del players[change[0]-offset]
        for i in range(len(result)):
            if not result[i]:
                result[i] = (i+offset,players[0][0])
                del players[0]
    except:
        cur = await db.execute("select userId from Users where score is not null order by score desc")
        res = await cur.fetchall()
        ids = [id[0] for id in res]

        for i, id in enumerate(ids, start = 1):
            await db.execute("update Users set rank = ? where userId = ?", (i, id))

        await db.commit()
        return
    #finally, update new ranks
    for rank, id in result:
        await db.execute("update Users set rank = ? where userId = ?", (rank,id))

    log(f"{len(changes)} places changed in the leaderboard")
    if commit:
        await db.commit()


async def getRankings(db: aiosqlite.Connection, start = 1, end = 20):
    cur = await db.execute("select userId, name, score from Users where rank between ? and ? order by rank asc", (start, end))
    res = await cur.fetchall()
    return [(a[0], a[1], str(round(a[2],1))) for a in res]



async def getSent(db: aiosqlite.Connection, days = 7):
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute(
        """select Users.userId, name, sum(Rounds.linesSent) as Sent from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null group by Users.userId having Sent > 0 order by Sent desc""", 
        (date_now-timedelta(days=days),))
    sent = await cur.fetchall()
    
    return [(combo[0], combo[1], f"{thousandsSeparator(combo[2])}") for combo in sent]

async def getavgSPM(db: aiosqlite.Connection, days = 7, requiredMatches = requiredMatchesSPM, rawdata = False):
    if days == 1:
        requiredMatches //= 4
    elif days == 2:
        requiredMatches //=3
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute(
        """select Users.userId, name, round(60*cast(sum(Rounds.linesSent) as float)/sum(playDuration),1) as avgSPM, count(Rounds.roundId) as c from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null and ruleset = 0 group by Users.userId having avgSPM > 0 and c> ? order by avgSPM desc""", 
        (date_now-timedelta(days=days),requiredMatches))

    spm = await cur.fetchall()

    if rawdata:
        return [(combo[0], combo[1], combo[2]) for combo in spm]
    else:
        return [(combo[0], combo[1], f"**{combo[2]:.2f}** in {combo[3]} matches" ) for combo in spm]



async def getavgOPM(db: aiosqlite.Connection, days = 7, requiredMatches = requiredMatchesOPM):
    if days == 1:
        requiredMatches //= 4
    elif days == 2:
        requiredMatches //=3
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute(
        """select Users.userId, name, round(60*cast(sum(Rounds.linesSent+Rounds.linesBlocked) as float)/sum(playDuration),1) as avgSPM, count(Rounds.roundId) as c from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null and ruleset = 0 group by Users.userId having avgSPM > 0 and c> ? order by avgSPM desc""", 
        (date_now-timedelta(days=days),requiredMatches))
    spm = await cur.fetchall()


    return [(combo[0], combo[1], f"**{combo[2]}** in {combo[3]} matches" ) for combo in spm]


async def getavgOPB(db: aiosqlite.Connection, days = 7, requiredMatches = requiredMatchesOPB):
    if days == 1:
        requiredMatches //= 4
    elif days == 2:
        requiredMatches //=3
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute(
        """select Users.userId, name, round(100*cast(sum(Rounds.linesSent+Rounds.linesBlocked) as float)/sum(blocks),1) as avgSPM, count(Rounds.roundId) as c from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null and ruleset = 0 group by Users.userId having avgSPM > 0 and c> ? order by avgSPM desc""", 
        (date_now-timedelta(days=days),requiredMatches)) 
    spm = await cur.fetchall()

    return [(combo[0], combo[1], f"**{combo[2]}%** in {combo[3]} matches" ) for combo in spm]


async def getavgBPM(db: aiosqlite.Connection, days = 7, requiredMatches = requiredMatchesBPM):
    if days == 1:
        requiredMatches //= 4
    elif days == 2:
        requiredMatches //=3
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute(
        """select Users.userId, name, round(60*cast(sum(Rounds.blocks) as float)/sum(playDuration),1) as avgBPM, count(Rounds.roundId) as c from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null group by Users.userId having avgBPM > 0 and c> ? order by avgBPM desc""", 
        (date_now-timedelta(days=days),requiredMatches))
    spm = await cur.fetchall()

    return [(combo[0], combo[1], f"**{combo[2]}** in {combo[3]} matches" ) for combo in spm]


async def getBlockedPercent(db: aiosqlite.Connection, days = 7, requiredMatches = requiredMatchesBlockedPercent):
    if days == 1:
        requiredMatches //= 4
    elif days == 2:
        requiredMatches //=3
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute(
        """select Users.userId, name, round(100*cast(sum(Rounds.linesBlocked) as float)/sum(Rounds.linesGot),1) as avgSPM, count(Rounds.roundId) as c from Rounds 
        inner join Users on Users.userId = Rounds.userId 
        inner join Matches on Matches.roundId = Rounds.roundId 
        where start > ? and Users.userId is not null and ruleset = 0 group by Users.userId having avgSPM > 0 and c> ? order by avgSPM desc""", 
        (date_now-timedelta(days=days),requiredMatches)) 
    spm = await cur.fetchall()

    return [(combo[0], combo[1], f"**{combo[2]}%** in {combo[3]} matches" ) for combo in spm]

async def getPower(db: aiosqlite.Connection, days = 7, requiredMatches = 40):
    def power(roomsize, opm):
        #without multiplying by 37.88... first. it'll be multiplied at the end (small optimization)
        if 1 < roomsize < 10:
            return opm/powerTable.get(roomsize)
        else:
            return opm/(3*roomsize + 29.4)

    if days == 1:
        requiredMatches //= 4
    elif days == 2:
        requiredMatches //=3
    #normalized opm
    date_now = datetime.now(tz = timezone('UTC'))

    PowerDict = dict()
    UsersDict = dict() #Might be worth to keep track of Userid-username via db
    query = db.execute("""
        select roomsize, 
            Users.userId,
            name, 
            60*(rounds.linesSent + rounds.linesBlocked)/playDuration as OPM 
            from Rounds join Users   on Rounds.UserId = Users.userId 
                        join Matches on Matches.roundId = Rounds.roundId 
            where ruleset = 0 and 
                  roomsize > 1 and
                  playDuration and 
                  start > ?
""", (date_now-timedelta(days=days),))
    
    async with query as rounds:
        async for round in rounds:
            if round["OPM"] is None: #meaning playDuration is 0
                continue

            if PowerDict.get(round["userId"]):
                PowerDict[round["userId"]].append(power(round["roomsize"],round["OPM"]))
            else:
                PowerDict[round["userId"]] = [power(round["roomsize"],round["OPM"])]
                UsersDict[round["userId"]] = round["name"]
    

    return [(x[0], x[1], f"**{x[2]:.1f}** in {x[3]} matches") for x in 
        sorted([
        (player,
        UsersDict[player],
        powerTable.get(2)*sum(PowerDict[player])/len(PowerDict[player]),
        len(PowerDict[player])
        )             
             for player in PowerDict], 
          key=lambda x: x[2], reverse=True)
    ]


async def getPowerB(db: aiosqlite.Connection, days = 7, requiredMatches = 40):
    def power(roomsize, opm):
        #without multiplying by 37.88... first. it'll be multiplied at the end (small optimization)
        if 1 < roomsize < 10:
            return opm/powerTable.get(roomsize)
        else:
            return opm/(3*roomsize + 29.4)

    if days == 1:
        requiredMatches //= 4
    elif days == 2:
        requiredMatches //=3
    #normalized opm
    date_now = datetime.now(tz = timezone('UTC'))

    PowerDict = dict()
    UsersDict = dict() #Might be worth to keep track of Userid-username via db
    TimeDict = dict()
    query = db.execute("""
        select roomsize, 
            Users.userId,
            name, 
            60*(rounds.linesSent + rounds.linesBlocked) as OPM,
            playDuration 
            from Rounds join Users   on Rounds.UserId = Users.userId 
                        join Matches on Matches.roundId = Rounds.roundId 
            where ruleset = 0 and 
                  roomsize > 1 and
                  playDuration and 
                  start > ?
""", (date_now-timedelta(days=days),))
    
    async with query as rounds:
        async for round in rounds:
            if round["OPM"] is None: #meaning playDuration is 0
                continue

            if PowerDict.get(round["userId"]):
                PowerDict[round["userId"]].append(power(round["roomsize"],round["OPM"]))
                TimeDict[round["userId"]] += round["playDuration"]
            else:
                PowerDict[round["userId"]] = [power(round["roomsize"],round["OPM"])]
                UsersDict[round["userId"]] = round["name"]
                TimeDict[round["userId"]] = round["playDuration"]
    

    return [(x[0], x[1], f"**{x[2]:.1f}** in {x[3]} matches") for x in 
        sorted([
        (player,
        UsersDict[player],
        powerTable.get(2)*sum(PowerDict[player])/TimeDict[player],
        len(PowerDict[player])
        )             
             for player in PowerDict], 
          key=lambda x: x[2], reverse=True)
    ]



async def getPPB(db: aiosqlite.Connection, days = 7, requiredMatches = 40):
    def ppb(roomsize, opb):
        #without multiplying by 37.88... first. it'll be multiplied at the end (small optimization)
        if 1 < roomsize < 10:
            return opb/powerTable.get(roomsize)
        else:
            return opb/(3*roomsize + 29.4)

    if days == 1:
        requiredMatches //= 4
    elif days == 2:
        requiredMatches //=3
    #normalized opb
    date_now = datetime.now(tz = timezone('UTC'))

    PowerDict = dict()
    UsersDict = dict() #Might be worth to keep track of Userid-username via db
    query = db.execute("""
        select roomsize, 
            Users.userId,
            name, 
            100.0*(rounds.linesSent + rounds.linesBlocked)/blocks as OPB 
            from Rounds join Users   on Rounds.UserId = Users.userId 
                        join Matches on Matches.roundId = Rounds.roundId 
            where ruleset = 0 and 
                  roomsize > 1 and
                  playDuration and 
                  start > ?
""", (date_now-timedelta(days=days),))
    
    async with query as rounds:
        async for round in rounds:
            if round["OPB"] is None: #meaning blocks is 0
                continue

            if PowerDict.get(round["userId"]):
                PowerDict[round["userId"]].append(ppb(round["roomsize"],round["OPB"]))
            else:
                PowerDict[round["userId"]] = [ppb(round["roomsize"],round["OPB"])]
                UsersDict[round["userId"]] = round["name"]
    

    return [(x[0], x[1], f"**{x[2]:.1f}%** in {x[3]} matches") for x in 
        sorted([
        (player,
        UsersDict[player],
        powerTable.get(2)*sum(PowerDict[player])/len(PowerDict[player]),
        len(PowerDict[player])
        )             
             for player in PowerDict if len(PowerDict[player]) > requiredMatches], 
          key=lambda x: x[2], reverse=True)
    ]





async def userCheeseTimes(db: aiosqlite.Connection, userId, days=7, limit = 20):
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute(
        """
    select 
        round(playDuration,2) as time, 
        round(60*blocks/playDuration,1) as BPM
    from Rounds join Matches on Rounds.roundId = Matches.roundId 
    where   ruleset = 1 
        and not cheeserows 
        and blocks > 8 
        and maxCombo > 2 
        and userId = ? 
        and start > ?
    order by playDuration asc limit ?
""", 
    (userId, date_now-timedelta(days=days), limit))

    times = await cur.fetchall()

    return times


async def userComboSpread(db: aiosqlite.Connection, userId, days=7):
    date_now = datetime.now(tz = timezone('UTC'))
    cur = await db.execute("""
    select maxCombo, count(*) from 
        Rounds join Matches on Rounds.roundId = Matches.roundId 
        where ruleset = 0 and 
            userId = ? and 
            start > ?
        group by maxCombo
        """,
    (userId, date_now-timedelta(days=days)))
    combos = await cur.fetchall()

    return combos


async def refresh_rankings(db: aiosqlite.Connection, refresh_limit: int):
    """
    Finds all the players in the top [refresh_limit] that haven't played in the last week and updates those.
    """

    date_now = datetime.now(tz = timezone('UTC'))
    #Gets inactive players
    inactive_users = await db.execute("""
        with RecentRounds as 
            (select distinct userId from 
                Rounds join Matches
                    on Rounds.roundId = Matches.roundId 
                where start > ?)

        select Users.userId, Users.name from 
            Users left join RecentRounds 
                on RecentRounds.userId = Users.userId 
            where RecentRounds.userId is null and 
                Users.rank < ?
        """,
        (date_now - timedelta(7), refresh_limit)) 

    #Updates their score
    async for userId, _ in inactive_users:
        await update_profile_data(db, userId)

    #Sort the leaderboard
    cur = await db.execute("select userId from Users where score is not null order by score desc")
    res = await cur.fetchall()
    ids = [id[0] for id in res]

    for i, id in enumerate(ids, start = 1):
        await db.execute("update Users set rank = ? where userId = ?", (i, id))
    
    await db.commit()





if __name__ == "__main__":
    async def main():
        db = await aiosqlite.connect(r"files\cultris.db")
        db.row_factory = aiosqlite.Row
        stats = await time_based_stats(db, 5840, days=30)
        print(stats)
        # leaderboard = await getPowerB(db, 30)
        # for l in leaderboard:
        #     print(f"{l[1]} {l[2]}")
        return
    asyncio.run(main())
