from database import *
from time import sleep


# TODO: Discord command that englobes all stat leaderboards
# TODO: Make it clearer what each stat leaderboard does
# TODO: Make it so main.py and bot.py can run asynchronously
# TODO: Go through all functions and place try: except:s appropiately
# TODO: Figure out how to use before_invoke and after_invoke
# TODO: Better logging, in different files
# TODO: Possibly to use thousands point in /legacystats to read the number better and /sent leaderboard
# TODO: Automate netscores obtention
# TODO: Remove the "Did you mean this player" message when the difference is capitalization
# TODO: Change the method to get top 5 Cheese times to the one using cheeseRows
# TODO: Function that adds stuff from cultris.db to fullCultris.db




if __name__ == "__main__":
    db = sqlite3.connect(r"files\cultris.db")

    while True:
        update_userlist(db)
        oldRound = newest_round(db)
        add_new_rounds(db)
        newRound = newest_round(db)
        process_data(db, oldRound+1, newRound)
        update_ranks(db, oldRound+1, newRound, commit=True)
        
        delete_old_data(db)
        sleep(60)

