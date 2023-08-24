# C2-stats-bot

Discord bot that displays Cultris II stats.

### TODO list

- Really should transform code to async at some point
- Go through all functions and place try: except:s appropiately
- (in database.py) check if any queries break when userId or similar is null
- Give message when a user DM's the bot   
- Deal with website being down. Test it
- database backups
- Max SPM, Max Sent
- Command that finds a player in all leaderboards
- Delete old logging
- FFA Notification system
- Fix database is locked error when a round is added but not processed
- Safe way of closing the bot
- in /stats : toggle button between PC view (aligned embed) and Phone embed (disaligned embed but readable in phone)
- /rounds command for a player rounds
- in /online : if all players in a room are afk, these players wont be displayed