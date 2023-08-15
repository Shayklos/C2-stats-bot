import sqlite3

"""
Meant to add values from cultris.db to fullCultris.db. 
It deletes the fullCultris Users table and fills it up with the values from cultris.db,
and it adds non existent Matches/Rounds to fullCultris.db
"""

def values(tuple: tuple) -> str:
    # (1,2,3,4,5) -> (?, ?, ?, ?, ?)
    return " (" + "?, " * (len(tuple)-1) + "?)"
 

def updateUsers(dbfrom: sqlite3.Connection, dbto: sqlite3.Connection):
    """
    Copies the Users table of smalldb to fulldb
    """
    # dbfrom.row_factory = sqlite3.Row
    dbto.execute("delete from Users") 
    users = dbfrom.execute("select * from Users")
    
    for user in users:
        dbto.execute("insert into Users values" + values(user), user)

    dbto.commit()


def addRounds(dbfrom: sqlite3.Connection, dbto: sqlite3.Connection):
    maxID = dbto.execute("select max(RoundId) from Rounds").fetchone()
    matches = dbfrom.execute("select * from Matches where roundId > ?", maxID)
    rounds = dbfrom.execute("select * from Rounds where roundId > ?", maxID)

    for match in matches:
        dbto.execute("insert into Matches values" + values(match), match)

    for round in rounds:
        dbto.execute("insert into Rounds values" + values(round), round)

    dbto.commit()


def updateDatabase(dbfrom: sqlite3.Connection,  dbto: sqlite3.Connection):
    if type(dbfrom) == type(dbto) == str:
        dbfrom = sqlite3.connect(dbfrom)
        dbto = sqlite3.connect(dbto)

    updateUsers(dbfrom, dbto)
    addRounds(dbfrom, dbto)


if __name__ == "__main__":
    fulldb = sqlite3.connect("files/fullCultris.db")
    smalldb = sqlite3.connect("files/cultris.db")
    updateDatabase(smalldb, fulldb)