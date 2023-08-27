from database import *
from methods import *
from time import sleep
import asyncio
import bot, traceback
import multiprocessing
from sys import version


async def gather_data():    
    if bot.developerMode:
        print(version)
        print("DEVELOPER MODE")

    db = await aiosqlite.connect(r"files\cultris.db", check_same_thread=False)
    while True:
        await update_userlist(db)
        oldRound = await newest_round(db)
        await add_new_rounds(db)
        newRound = await newest_round(db)
        await process_data(db, oldRound+1, newRound)
        await update_ranks(db, oldRound+1, newRound, commit=True)
        await delete_old_data(db)
        await check_netscores(db)
        await check_rankings(db)

        await asyncio.sleep(30)

async def main():
    gatherData = asyncio.create_task(gather_data())
    c2Bot = asyncio.create_task(bot.cultrisBot.start(bot.TOKEN))
    await gatherData 
    await c2Bot



if __name__ == "__main__": 
    try:
        asyncio.run(main())
    except Exception as e:
        log(traceback.format_exc(), file='files/log_errors.txt')

