import sqlite3, json, urllib.request
from math import exp, log, sqrt, pi
from settings import LIVEINFO_URL

from random import choice
import time 
import asyncio


db = sqlite3.connect("files/elo.db")
RANKED_TAG = "[Ranked]"

db.execute("""
CREATE TABLE IF NOT EXISTS "Glicko" (
	"userId"	UNSIGNED INTEGER,
	"name"	VARCHAR(255),
	"rank"	UNSIGNED INTEGER,
	"rating" REAL DEFAULT 1500.0,
  "RD" REAL DEFAULT 350.0,
  "volatility" REAL DEFAULT 0.06,
	"maxCombo"	INTEGER DEFAULT 0,
	"playedRounds"	INTEGER DEFAULT 0,
	"wins"	INTEGER DEFAULT 0,
	"maxBPM"	REAL DEFAULT 0.0,
	"avgBPM"	REAL DEFAULT 0.0,
	"linesGot"	INTEGER DEFAULT 0,
	"linesSent"	INTEGER DEFAULT 0,
	"linesBlocked"	INTEGER DEFAULT 0,
	"blocksPlaced"	INTEGER DEFAULT 0,
	"14s"	INTEGER DEFAULT 0,
	"13s"	INTEGER DEFAULT 0,
	"12s"	INTEGER DEFAULT 0,
	"11s"	INTEGER DEFAULT 0,
	"10s"	INTEGER DEFAULT 0,
	"peakRank"	INTEGER,
	"peakRankScore"	REAL,
	"comboSum"	INTEGER DEFAULT 0,
	"playedMin"	REAL,
	PRIMARY KEY("userId")
           
);""")


class Player():
    """
    Represents a player, with their rating, rating deviation (RD) and volatility of Glicko-2.
    """
    #System constant, smaller tau, smaller changes in volatility
    tau = 0.4 

    #Convergence tolerance, using the one suggested in paper http://www.glicko.net/glicko/glicko2.pdf
    epsilon = 0.000001  

    def __init__(self, id: int, rating = 1500, RD = 350, volatility  = 0.06):
        self.id = id


        self.rating = rating
        self.RD = RD
        self.volatility  = volatility 
        self.CR = self.calculate_CR()

        self.mu = (self.rating - 1500)/173.7178
        self.phi = self.RD/173.7178

    def do_glicko(self, opponent, win = True):
        #Step 3, 4
        
        g = lambda phi : 1 / sqrt(1 + 3 * (phi/pi)**2)
        E = lambda mu, phi : 1 / (1 + exp( -g(phi) * (self.mu - mu) ))
        
        opponent_E = E(opponent.mu, opponent.phi)

        v = 1/(g(opponent.phi)**2 * opponent_E*(1-opponent_E)) 

        delta = v*g(opponent.phi)*(win-opponent_E)


        #Step 5
        a = 2*log(self.volatility)
        f = lambda x : (exp(x)*(delta**2 - self.phi**2 - v - exp(x) )) / (2*(self.phi**2 + v + exp(x))**2) - (x-a)/Player.tau**2

        A = a
        if delta**2 > self.phi**2 + v:
            B = log(delta**2 - self.phi**2 - v)
        else:
            k = 1
            while f(a - k*Player.tau) < 0:
                k += 1
            B = a - k*Player.tau

        fA = f(A)
        fB = f(B)

        while abs(B-A) > Player.epsilon:
            C = A + (A-B)*fA/(fB-fA)
            fC = f(C)
            if fC * fB > 0:
                fA /= 2
            else:
                A = B 
                fA = fB 
            B = C 
            fB = fC 
        self.volatility = exp(A/2)
        #Step 6
        phistar = sqrt(self.phi**2 + self.volatility**2)

        self.new_phi = 1/sqrt(1/phistar**2 + 1/v)
        self.new_mu = self.mu + self.new_phi**2 * g(opponent.phi)*(win - opponent_E)



    def __str__(self):
        print(f"""{self.name}:
    Rating = {self.rating}
    Rating Deviation = {self.RD}
    Volatility = {self.volatility}
    CR = {self.CR}""")


    def update(self):
        self.mu = self.new_mu
        self.phi = self.new_phi

        self.rating = 173.7178*self.mu + 1500
        self.RD = 173.7178*self.phi
        self.CR = self.calculate_CR()

        
    def calculate_CR(self):
        return round(25_000 / (1 + 10 ** ( ( (1500 - self.rating) * pi ) / sqrt( 3 + log(10)**2 * self.RD ** 2 + 2500*( 64*pi**2 + 147 * log(10) ** 2 ) )) ), 2)


class Match():
    Pool = []

    def __init__(self, player1: Player, player2: Player):
           self.player1 = player1
           self.player2 = player2 
           self.winner = None
           self.isFinished = False
           self.inProgress = False

    def finish(self):
        if not self.isFinished:
            return
        
        self.player1.do_glicko(self.player2, self.winner == self.player1)
        self.player2.do_glicko(self.player1, self.winner == self.player2)

        self.player1.update()
        self.player2.update()


    async def expectResult(self, roomid):
        liveinfo = getLiveinfo()
        #check if the room no longer exists
        #check if only two or less players are playing
        #check that the same two players are always playing
        #check who wins, secure it doesnt get lost when score is resetted 

        self.score1 = self.score2 = 0
        self.inProgress = True
        while not self.isFinished:
            liveinfo = getLiveinfo()
 
            for player in liveinfo.get("players"): #this loop could be optimized
                if player.get("id") == self.player1.id:
                    self.score1 = player.get("currentscore")
                elif player.get("id") == self.player2.id:
                    self.score2 = player.get("currentscore")
            
            if max(self.score1, self.score2) >= 11 and abs(self.score1 - self.score2) > 1: #First to 11, win by 2
                self.winner = self.player1 if self.score1 > self.score2 else self.player2 
                self.isFinished = True

            await asyncio.sleep(10)
            



# Shay = Player("Player 1", 1900, 100)
# Azteca = Player("Player 2", 1900, 40)

# match = Match(Shay, Azteca)

# for _ in range(100):
#     match.winner = choice((Shay, Azteca)) 
#     match.finish() 

# Shay.stats()
# Azteca.stats()

def getLiveinfo():
    with urllib.request.urlopen(LIVEINFO_URL) as URL:
        return json.load(URL)



def lookForMatch():
    liveinfo = getLiveinfo()

    #Obtain [Ranked] rooms
    ranked_rooms = []
    for room in liveinfo.get("rooms"):
        if RANKED_TAG in room.get("name"):
            ranked_rooms.append(room.get("id"))
    
    #Get players in the Ranked rooms
    for room_id in ranked_rooms:
        players = []
        for player in liveinfo.get("players"):
            #The players must be registered
            if not player.get("guest") and player.get("room") == room_id:
                players.append(player.get("id"))

        if len(players) == 2:
            # TODO : check match doesnt already exist
            Match.Pool.append(Match(
                Player(players[0]),
                Player(players[1])
            ))
    

        
async def glickoLoop():
    lookForMatch()
    if not Match.Pool: #No ranked play
        return
    
    for match in Match.Pool:
        match: Match
        if match.isFinished:
            match.finish()
            Match.Pool.remove(match)
        if match.inProgress:
            continue
        match.expectResult()



lookForMatch()