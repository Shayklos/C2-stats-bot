# C2-stats-bot

Discord bot that displays Cultris II stats.


### Deployment
1. Make sure to have access to the Cultris II API endpoints. You can ask either me or the developer of the game via email `de@iru.ch`.

### Logging database
The project now uses a **separate SQLite file** for logging (default `files/log.db`).  This keeps diagnostics apart from the main Cultris data (`cultris2.db`).

To initialise the logging database:

1. Run `python -m database.setup_logging_db` (preferred) or
   `python database/setup_logging_db.py` – both modes are supported. Either
   command will create any missing tables in the log file and the `log_view`.

By default the main database is still `cultris2.db`; pass an alternate path to
`Database.connect(stats_path, log_path)` when creating the connection if you
need to change either location.
2. Optionally seed functions/concepts by editing the script or using the helper methods from `database.Database`.

The logging schema consists of three tables:

* `functions` – unique names of functions that perform logging.
* `concepts` – templates containing replacement symbols (`~&`, `~=`, `~¿` for text and
  `~¡`, `~*`, `~%` for numbers).
* `logs` – each row references a function and a concept, records a UTC timestamp, and
  stores up to three text and three numeric parameters.

A SQL view named `log_view` produces messages by substituting the symbols with
provided parameters – the resulting string is available as the `message` column.

#### Using from code

The `database.Database` class exposes:

```python
await db.log_event(
    function_name: str,
    concept: str | Concept,  # Can be a ConceptDef constant or string template
    category: CategoryEnum | None = None,
    text_params: list[str] | None = None,
    num_params: list[float] | None = None,
)
```

**Using predefined Concept constants (recommended):**
```python
from database.database_models import Concept, CategoryEnum

await db.log_event(
    "my_function",
    Concept.UpdateUser,  # Type-safe concept constant
    text_params=["username"],
    num_params=[user_id]
)
```

**With category override:**
```python
await db.log_event(
    "my_function",
    Concept.UpdateUser,
    category=CategoryEnum.DISCORD,
    text_params=["username"]
)
```

**Backward compatible string templates:**
```python
await db.log_event(
    "my_function",
    "User ~& logged in",  # Still works
    text_params=["username"]
)
```

Helpers `ensure_function`/`ensure_concept` insert entries if missing. A convenience
wrapper `db_log` in `methods.py` will automatically capture the caller name and accepts
up to three text and numeric params:

```python
from methods import db_log

await db_log(db, "User ~& logged in", username)
```

Existing code such as `logInteraction` has been updated to call `db_log` if the
bot object exposes a `db` attribute.

These additions keep logging clean and maintainable while retaining the
original file-based logging behavior.

### TODO (or ideas) list

- database backups
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
   ACHIEVEMENTS_URL=<achievements endpoint>

   #Only required for connection with Def's VPS for profile pictures
   VPS_USERNAME=<vps username>
   VPS_PASSWORD=<vps password>

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
