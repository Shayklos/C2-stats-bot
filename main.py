from database import *
from methods import *
from settings import gatherDataRefreshRate
from os.path import join
import bot
import asyncio, traceback



async def gather_data():
    """
    This loop connects to gewaltig api and:
        -Updates the userlist: Adds to the database newly registered users
        -Adds new rounds: Collects matches/rounds that are not in the database already
        -Processes new data: Updates user data from the rounds added in the last step
        -Updates ranks: Filters the people who played in FFA in recent rounds, and updates their rank and scores
        -Deletes old data: Deletes matches/rounds from the database that are older than 30 days (by default)
        -Checks netscores: Checks if 24h have passed since the netscores were last updated, and updates them if it has. 
        -Checks rankings: Checks if a week has passed the rankings of inactive players were last updated, and updates them if it has.
    """
    if bot.developerMode:
        from sys import version
        print(version)
        print("DEVELOPER MODE")

    db = await aiosqlite.connect(join('files', 'cultris.db'), check_same_thread=False)
    db.row_factory = aiosqlite.Row
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

        await asyncio.sleep(gatherDataRefreshRate) #by default 30s

async def main():
    gatherData = asyncio.create_task(gather_data())
    c2Bot = asyncio.create_task(bot.cultrisBot.start(bot.TOKEN))
    # updateFullDB = asyncio.create_task(update_fulldb()) #Uncomment if in possesion of fullDB

    await gatherData   # Data addition loop
    await c2Bot        # Discord bot loop
    # await updateFullDB # Full DB data gathering



if __name__ == "__main__": 
    try:
        asyncio.run(main())
    except Exception as e:
        log(traceback.format_exc(), file=join('files', 'log_error.txt'))

