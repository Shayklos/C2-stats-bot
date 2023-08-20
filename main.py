from database import *
from methods import *
from time import sleep
import asyncio
import bot, traceback
import multiprocessing
from sys import version

# TODO: Really should transform code to async at some point
# TODO: Go through all functions and place try: except:s appropiately
# TODO: (in database.py) check if any queries break when userId or similar is null
# TODO: Give message when a user DM's the bot   
# TODO: Look into /leaderboard rankings fast=False
# TODO: Deal with website being down. Test it
# TODO: database backups
# TODO: Max SPM, Max Sent
# TODO: Function that finds a player in all leaderboards
# TODO: Lower required matches for leaderboards when days is low
# TODO: Delete old logging
# TODO: Update leaderboard every now and then
# TODO: FFA Notification system
# TODO: Week up/down in /stats /leaderboard
# TODO: Fix database is locked error when a round is added but not processed
# TODO: Disable week/day buttons when they reached limit
# TODO: /leaderboard Netscores breaks when days>7 with buttons
# TODO: Safe way of closing the bot

def main()->None:    
    if bot.developerMode:
        print(version)
        print("DEVELOPER MODE")

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
        check_rankings(db)

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
        log(traceback.format_exc(), file='files/log_errors.txt')

