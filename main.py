from database import *
from methods import *
from time import sleep
import asyncio, aiosqlite
import bot, traceback
import threading
from apscheduler.schedulers.background import BackgroundScheduler

## TODO: Make it so main.py and bot.py can run asynchronously
# TODO: Go through all functions and place try: except:s appropiately
## TODO: Better logging, in different files
# TODO: Automate netscores obtention
# TODO: Function that adds stuff from cultris.db to fullCultris.db
# TODO: (in database.py) check if any queries break when userId or similar is null
# TODO: Give message when a user DM's the bot   
# TODO: Look into /leaderboard rankings fast=False



def main()->None:    
    db = sqlite3.connect(r"files\cultris.db", check_same_thread=False)

    while True:
        # with db:
        update_userlist(db)
        oldRound = newest_round(db)
        add_new_rounds(db)
        newRound = newest_round(db)
        process_data(db, oldRound+1, newRound)
        update_ranks(db, oldRound+1, newRound, commit=True)
        
        delete_old_data(db)
        sleep(30)




if __name__ == "__main__": 
    try:
        t1 = threading.Thread(target=main, args=())
        t1.start()

        # db = sqlite3.connect(r"files\cultris.db", check_same_thread=False)
        # add_recent_profile_data(db,7,True,True)
        
        asyncio.run(bot.client.start(bot.TOKEN))
        while True:
            pass
    except Exception as e:
        log(traceback.format_exc())