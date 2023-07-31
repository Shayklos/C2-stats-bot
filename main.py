from database import *
from methods import *
from time import sleep
import asyncio
import bot, traceback
import threading, multiprocessing
from sys import version
# TODO: Go through all functions and place try: except:s appropiately
# TODO: Function that adds stuff from cultris.db to fullCultris.db
# TODO: (in database.py) check if any queries break when userId or similar is null
# TODO: Give message when a user DM's the bot   
# TODO: Look into /leaderboard rankings fast=False
# TODO: Deal with website being down
# TODO: Distribution plots

def main()->None:    
    print(version)

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
        check_netscores(db)

        sleep(30)




if __name__ == "__main__": 
    try:
        # print(is_locked)
        p = multiprocessing.Process(target=main, args=())
        p.start()

        # db = sqlite3.connect(r"files\cultris.db", check_same_thread=False)
        # add_recent_profile_data(db,7,True,True)
        
        asyncio.run(bot.client.start(bot.TOKEN))
        while True:
            sleep(1)
    except Exception as e:
        log(traceback.format_exc())