from database import *
from methods import *
from time import sleep
import asyncio
import bot, traceback
import multiprocessing
from sys import version


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

