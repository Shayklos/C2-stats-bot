from datetime import datetime, timezone
import sqlite3

db = sqlite3.connect("files/log.db")

def convertToPOSIX(str, format = "[%Y-%m-%d] [%H:%M:%S]", timezone = timezone.utc) -> int:
    return datetime.strptime(str, format).replace(tzinfo=timezone).timestamp()


def isINT(str: str) -> bool:
    try:
        int(str)
    except:
        return False
    return True

def log_generalToDB(db: sqlite3.Connection):
    with open("files/log_general.txt", "r") as log:
        lines = log.readlines()

    for i, line in enumerate(lines[:-1]):
        try:
            time = convertToPOSIX(line[:23])
            text = line[24:].split(' ')
            if text[0] == 'Added':
                if isINT(text[1]):
                    db.execute("insert into General (date, kind, value) values (?, ?, ?)",
                               (time, "Added matches", text[1]))
                else:
                    if text[1] == 'user':
                        db.execute("insert into General (date, kind, value, name) values (?, ?, ?, ?)",
                                (time, "New player account", text[2], text[3][1:-1]))
                    else:
                        db.execute("insert into General (date, kind, name) values (?, ?, ?)",
                                (time, "Update player data", text[1])) 
            elif text[0] == 'Deleted':
                db.execute("insert into General (date, kind, value) values (?, ?, ?)",
                               (time, "Delete matches", text[1]))
            elif text[0] == 'Updated':
                db.execute("insert into General (date, kind, name) values (?, ?, ?)",
                                (time, "Update player data", text[1]))
            elif text[0] == 'Processed':
                db.execute("insert into General (date, kind, value) values (?, ?, ?)",
                               (time, "Process rounds data", text[1]))
            elif isINT(text[0]):
                db.execute("insert into General (date, kind, value) values (?, ?, ?)",
                               (time, "Leaderboard swaps", text[1]))
            else:
                db.execute("insert into General (date, kind, name, value) values (?, ?, ?, ?)",
                                (time, "New player account", text[3], text[4][1:-1]))
        except:
            print(i, line)
            input()
    db.commit()

if __name__ == "__main__":
    log_generalToDB(db)