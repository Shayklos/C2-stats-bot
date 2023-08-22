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
# TODO: Deal with website being down. Test it
# TODO: database backups
# TODO: Max SPM, Max Sent
# TODO: Command that finds a player in all leaderboards
# TODO: Delete old logging
# TODO: FFA Notification system
# TODO: Fix database is locked error when a round is added but not processed
# TODO: Safe way of closing the bot
# TODO: in /stats : toggle button between PC view (aligned embed) and Phone embed (disaligned embed but readable in phone)
# TODO: /rounds command for a player rounds
# TODO BUG: in /online : if all players in a room are afk, these players wont be displayed


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
        
        asyncio.run(bot.cultrisBot.start(bot.TOKEN))
        while 1:
            sleep(1)
    except Exception as e:
        log(traceback.format_exc(), file='files/log_errors.txt')

