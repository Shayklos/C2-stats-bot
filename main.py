from database.database import Database
from methods import *
from settings import (gatherDataRefreshRate, randomChecksCurrent, checkRankingsEnabled, 
                      checkRankingsIntervalDays, checkRankingsThreshold, save_random_checks_current)
from os.path import join
import bot
import asyncio, traceback
from datetime import datetime, timedelta, timezone


async def gather_data():
    """
    This loop connects to gewaltig api and:
        -Updates the userlist: Adds to the database newly registered users
        -Adds new rounds: Collects matches/rounds that are not in the database already
        -Processes new data: Aggregates user combo and played round stats from the newly added rounds
        -Updates ranks: Recalculates user ranks based on their current scores
    """
    if bot.developerMode:
        from sys import version
        print(version)
        print("DEVELOPER MODE")

    db = await Database.connect(join('files', 'cultris2.db'), join('files', 'log.db'))
    
    while True:
        try:
            # Update userlist - fetch users starting from the next ID after the last one in DB
            last_user_id = await db.get_last_user_id()
            await db.update_userlist(last_user_id + 1)
            
            # Fetch and process rounds in batches until no more rounds are found
            while True:
                rounds_added = await db.process_next_round_batch(update_players = True)
                if rounds_added == 0:
                    break
            
            await db.update_rankings()

            await asyncio.sleep(gatherDataRefreshRate)  # by default 30s
            
        except Exception as e:
            try:
                await db.log_event(
                    "gather_data",
                    f"Error in gather_data loop: ~&",
                    text_params=[traceback.format_exc()],
                )
            except:
                pass
            await asyncio.sleep(gatherDataRefreshRate)


async def random_checks(db: Database):
    """
    Sequentially update every user in the database, cycling through them indefinitely.
    Stores the current position in settings.json to resume from where we left off.
    Updates one user per iteration.
    """
    last_user_id = await db.get_last_user_id()
    current_user_id = randomChecksCurrent
    
    while True:
        try:
            # Wrap around to user 1 if we've gone past the last user
            if current_user_id > last_user_id:
                current_user_id = 1
            
            # Update the user
            await db.update_user(current_user_id)
            
            # Save progress every time
            save_random_checks_current(current_user_id)
            
            current_user_id += 1
            
            # Sleep before next user
            await asyncio.sleep(gatherDataRefreshRate)
            
        except Exception as e:
            try:
                await db.log_event(
                    "random_checks",
                    f"Error updating user {current_user_id}: ~&",
                    text_params=[traceback.format_exc()],
                )
            except:
                pass
            current_user_id += 1
            await asyncio.sleep(gatherDataRefreshRate)


async def check_rankings(db: Database):
    """
    Periodically update all users with rank below the configured threshold.
    Runs every N days (configurable, default 7).
    """
    if not checkRankingsEnabled:
        return
    
    while True:
        try:
            # Sleep for the configured interval
            await asyncio.sleep(checkRankingsIntervalDays * 24 * 3600)
            
            # Get all users with rank below threshold
            user_ids = await db.get_users_with_rank_below(checkRankingsThreshold)
            
            for user_id in user_ids:
                try:
                    await db.update_user(user_id)
                except Exception as e:
                    try:
                        await db.log_event(
                            "check_rankings",
                            f"Error updating user {user_id}: ~&",
                            text_params=[traceback.format_exc()],
                        )
                    except:
                        pass
            
        except Exception as e:
            try:
                await db.log_event(
                    "check_rankings",
                    f"Error in check_rankings loop: ~&",
                    text_params=[traceback.format_exc()],
                )
            except:
                pass


async def c2_bot():
    """Discord bot event loop"""
    try:
        await bot.cultrisBot.start(bot.TOKEN)
    except Exception as e:
        # Cannot log to database from bot context
        print(f"Error in c2_bot: {traceback.format_exc()}")


async def main():
    db = await Database.connect(join('files', 'cultris2.db'), join('files', 'log.db'))
    
    gatherData = asyncio.create_task(gather_data())
    randomChecks = asyncio.create_task(random_checks(db))
    checkRankings = asyncio.create_task(check_rankings(db))
    c2Bot = asyncio.create_task(c2_bot())

    # await gatherData        # Data addition loop
    # await randomChecks      # Sequential user update loop
    # await checkRankings     # Periodic ranking check loop
    await c2Bot             # Discord bot loop


def init():
    """
    Setups directories needed for the bot to work
    """

    # Create files/logs folder. Move logs to this folder if they exist (from old versions of the bot)
    # move_log_files_to_logs_folder()

    # Create check_times file if it doesn't exist
    create_check_times_file()



if __name__ == "__main__": 
    try:
        init()
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {traceback.format_exc()}")

