# C2-stats-bot

Discord bot that displays Cultris II stats.

### TODO list

- Give message when a user DM's the bot   
- Deal with website being down. Test it
- database backups
- Max SPM, Max Sent
- Command that finds a player in all leaderboards
- Delete old logging
- FFA Notification system
- Fix database is locked error when a round is added but not processed
- Go through all functions and place try: except:s appropiately
- (in database.py) check if any queries break when userId or similar is null
- Safe way of closing the bot
- `/rounds` command for a player rounds
- in `/online` : if all players in a room are afk, these players wont be displayed
- in `/stats` : Maybe last hour stats?
- aiohttp 
- setting for required matches in `/leaderboard Power`