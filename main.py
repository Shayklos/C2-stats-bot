from database import *
from time import sleep

if __name__ == "__main__":
    # db = sqlite3.connect(r"files\fullCultris.db")

    while True:
        update_userlist(db)
        oldRound = newest_round(db)
        add_new_rounds(db)
        newRound = newest_round(db)
        process_data(db, oldRound+1, newRound)
        
        delete_old_data(db)
        sleep(30)