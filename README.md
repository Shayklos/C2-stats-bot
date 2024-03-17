# C2-stats-bot

Discord bot that displays Cultris II stats.


### Deployment
1. Make sure to have access to the Cultris II API endpoints. You can ask either me or the developer of the game via email `de@iru.ch`.
2. Create your own Discord bot. Currently the bot required permissions are:
   - Use Application Commands
   - Send messages
   - View channels

    If bot doesn't work as expected try to activate intents in the dev portal.
3. Place a `.env` file in the root folder that contains
   
   ```
   DISCORD_TOKEN=<your token>

   BASE_USER_URL=<user info endpoint>
   BASE_ROUNDS_URL=<matches info endpoint>
   LIVEINFO_URL=<liveinfo endpoint>

   #Everything that follows is for testing and is not needed otherwise
   DISCORD_TEST_TOKEN=0
   DISCORD_GUILD=name
   DISCORD_GUILD_ID=0
4. Run `main.py` to turn on the bot with data gathering, or run `bot.py` to just run the bot.
### TODO (or ideas) list

- database backups
- Command that finds a player in all leaderboards
- Delete old logging
- FFA Notification system
- in `/online` : if all players in a room are afk, these players wont be displayed
- in `/stats`, `/legacystats`, `/challenges`, `/online`: Interaction fails when website is down.  Send a message to user warning them of this
- 'news' every week
- Send notifications to a role when player count is higher than a certain number
- 95% stats: stats removing the worst 5% of them (or 2.5% worst and 2.5% best), to account for games with low stats due to rare mistakes, or opponent's mistake ending player's game too soon
