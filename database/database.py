import asyncio
from time import perf_counter, sleep
from sqlalchemy import text
from sqlalchemy import func
from sqlalchemy import select
import sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
import traceback
from os.path import join
import sys
import logging


# When this module is executed directly (`python database/database.py`)
# there is no enclosing package, which makes relative imports fail.  We can
# create a dummy `database` package entry in sys.modules so that the
# subsequent `from .foo import ...` statements work in both contexts.
if __package__ is None and __name__ == "__main__":
    import os, sys, types
    pkg = types.ModuleType("database")
    pkg.__path__ = [os.path.dirname(os.path.abspath(__file__))]
    sys.modules["database"] = pkg
    __package__ = "database"

# Now use straightforward relative imports everywhere.
from .Endpoint import Endpoint
from .migration import convert_rounds_range

# main application models
from .stats_models.UserPlayedRound import UserPlayedRound
from .stats_models.UserCombo import UserCombo
from .stats_models.User import User
from .stats_models.Achievement import Achievement
from datetime import datetime, timezone
from .stats_models.Match import Match
from .stats_models.Round import Round
from .stats_models.Team import Team
from .stats_models.Ruleset import Ruleset
from .stats_models.Netscore import Netscore

# shared declarative base imported from stats_models Base; this is used
# for the main (stats) database only.  Logging tables are kept in a separate
# metadata object (see LogBase below) so that they can reside in a different
# sqlite file.
from .stats_models.Base import Base

# logging tables base
from .log_models.Base import LogBase

# logging/database models
from .log_models.Function import Function
from .log_models.Concept import Concept as ConceptTable
from .log_models.ConceptDef import Concept, ConceptDef
from .log_models.Category import Category
from .log_models.CategoryEnum import CategoryEnum
from .log_models.LogEntry import LogEntry

# SQL used to create the view that formats the concept template with
# the parameters from the log row.  This view is created automatically
# when the database connects.
_LOG_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS log_view AS
SELECT
    l.id AS id,
    l.timestamp AS timestamp,
    f.name AS function_name,
    cat.text AS category,
    -- perform a series of REPLACE calls to substitute the six symbols
    -- with their corresponding parameter values (nulls become empty).
    REPLACE(
        REPLACE(
            REPLACE(
                REPLACE(
                    REPLACE(
                        REPLACE(
                            c.template,
                            '~&', COALESCE(l.param1_text, '')
                        ),
                        '~=', COALESCE(l.param2_text, '')
                    ),
                    '~¿', COALESCE(l.param3_text, '')
                ),
                '~¡', COALESCE(CAST(l.param1_num AS TEXT), '')
            ),
            '~*', COALESCE(CAST(l.param2_num AS TEXT), '')
        ),
        '~%', COALESCE(CAST(l.param3_num AS TEXT), '')
    ) AS message
FROM logs AS l
JOIN functions AS f ON l.function_id = f.id
JOIN concepts AS c ON l.concept_id = c.id
LEFT JOIN categories AS cat ON c.category_id = cat.id
ORDER BY l.id desc;
"""


class Database:
    def __init__(self, stats_engine: sqlalchemy.ext.asyncio.AsyncEngine, log_engine: sqlalchemy.ext.asyncio.AsyncEngine):
        # primary engine for application data
        self.engine = stats_engine
        # separate engine for logging; may point to same file if desired
        self.log_engine = log_engine

    @classmethod
    async def connect(cls, stats_db_filepath: str, log_db_filepath: str | None = None):
        """Create a Database instance.

        *stats_db_filepath* is the path to the main database (e.g. cultris2.db).  If
        *log_db_filepath* is omitted it defaults to the same path, preserving
        backwards compatibility.  To keep logging in a distinct file, provide a
        separate path such as "files/log.db".
        """
        stats_engine = sqlalchemy.ext.asyncio.create_async_engine(
            "sqlite+aiosqlite:///" + stats_db_filepath, echo=False
        )
        if log_db_filepath is None:
            log_db_filepath = stats_db_filepath
        log_engine = sqlalchemy.ext.asyncio.create_async_engine(
            "sqlite+aiosqlite:///" + log_db_filepath, echo=False
        )

        # create tables on stats engine
        async with stats_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # create tables & view on logging engine
        async with log_engine.begin() as conn:
            await conn.run_sync(LogBase.metadata.create_all)
            await conn.execute(text(_LOG_VIEW_SQL))

        db = Database(stats_engine, log_engine)
        await db.populate_categories()
        return db


    # helper methods for the logging database
    async def _get_or_create(self, session, model, **kwargs):
        """Return an instance matching kwargs or insert a new one.

        The session should already be within an async context manager.
        ``model`` is an ORM class mapped to the appropriate Base.
        """
        stmt = select(model).filter_by(**kwargs)
        result = await session.scalar(stmt)
        if result:
            return result
        instance = model(**kwargs)
        session.add(instance)
        # flush to populate primary key in case the caller needs it
        await session.flush()
        return instance

    async def ensure_function(self, session, name: str):
        return await self._get_or_create(session, Function, name=name)

    async def ensure_concept(self, session, template: str):
        return await self._get_or_create(session, ConceptTable, template=template)

    def log_event_async(
        self,
        function_name: str,
        concept: str | ConceptDef,
        category: CategoryEnum | None = None,
        text_params: list[str] | None = None,
        num_params: list[float] | None = None,
    ):
        """Schedule a log entry to be written asynchronously in the background.

        This method enqueues the logging operation without blocking the caller.
        Use this when logging should not impact performance of the main operation.
        """
        asyncio.create_task(self.log_event(
            function_name, concept, category, text_params, num_params
        ))

    async def log_event(
        self,
        function_name: str,
        concept: str | ConceptDef,
        category: CategoryEnum | None = None,
        text_params: list[str] | None = None,
        num_params: list[float] | None = None,
    ):
        """Insert a log entry, creating referenced function/concept if needed.

        **function_name** is the name of the calling function.
        **concept** can be either:
          - A `ConceptDef` constant (e.g., `Concept.UpdateUser`)
          - A string template for backward compatibility
        **category** is a `CategoryEnum` value. If not provided, uses the concept's default.
        **text_params** may contain up to three strings; **num_params** up to
        three numbers. Parameters are matched positionally to the symbols
        documented in the schema (~&, ~=, ~¿ for text; ~¡, ~*, ~% for numbers).
        Timestamp (UTC) is recorded automatically.
        """
        text_params = text_params or []
        num_params = num_params or []

        # Extract template and category from concept
        if isinstance(concept, ConceptDef):
            template = concept.template
            concept_category = category or concept.category
        else:
            template = concept
            concept_category = category

        async_session = async_sessionmaker(self.log_engine, expire_on_commit=False)
        async with async_session() as session:
            func = await self.ensure_function(session, function_name)
            
            # Get or create the concept
            stmt = select(ConceptTable).filter_by(template=template)
            conc = await session.scalar(stmt)
            if conc:
                # Update existing concept if category_id is not set
                if concept_category and conc.category_id is None:
                    cat = await self.ensure_category(session, concept_category.value)
                    conc.category_id = cat.id
            else:
                conc = ConceptTable(template=template)
                if concept_category:
                    cat = await self.ensure_category(session, concept_category.value)
                    conc.category_id = cat.id
                session.add(conc)
            
            await session.flush()

            entry = LogEntry(
                function_id=func.id,
                concept_id=conc.id,
                timestamp=datetime.now(timezone.utc),
                param1_text=text_params[0] if len(text_params) > 0 else None,
                param2_text=text_params[1] if len(text_params) > 1 else None,
                param3_text=text_params[2] if len(text_params) > 2 else None,
                param1_num=num_params[0] if len(num_params) > 0 else None,
                param2_num=num_params[1] if len(num_params) > 1 else None,
                param3_num=num_params[2] if len(num_params) > 2 else None,
            )
            session.add(entry)
            await session.commit()
            
            # Format and print the log message (mimics log_view)
            message = template
            message = message.replace('~&', entry.param1_text or '')
            message = message.replace('~=', entry.param2_text or '')
            message = message.replace('~¿', entry.param3_text or '')
            message = message.replace('~¡', str(entry.param1_num) if entry.param1_num is not None else '')
            message = message.replace('~*', str(entry.param2_num) if entry.param2_num is not None else '')
            message = message.replace('~%', str(entry.param3_num) if entry.param3_num is not None else '')
            
            category_str = concept_category.value if concept_category else "Uncategorized"
            print(f"\033[32m[{entry.timestamp.isoformat()}] \033[34m[{category_str}] \033[33m{function_name}\033[37m: {message}")
            
            return entry

    async def ensure_functions(self, names: list[str]):
        """Ensure that a list of function names exist in the _logging_ database.

        Operates on ``self.log_engine``.

        Returns a list of Function objects in the same order as *names*.
        """
        async_session = async_sessionmaker(self.log_engine, expire_on_commit=False)
        results = []
        async with async_session() as session:
            for name in names:
                obj = await self.ensure_function(session, name)
                results.append(obj)
            await session.commit()
        return results

    async def ensure_concepts(self, templates: list[str | ConceptDef]):
        """Ensure that a list of concept templates/definitions exist in the _logging_ database.

        Operates on ``self.log_engine``.
        
        Can accept either:
        - String templates for backward compatibility
        - ConceptDef objects with template and category
        """
        async_session = async_sessionmaker(self.log_engine, expire_on_commit=False)
        results = []
        async with async_session() as session:
            for item in templates:
                if isinstance(item, ConceptDef):
                    template = item.template
                    category = item.category
                else:
                    template = item
                    category = None
                
                stmt = select(ConceptTable).filter_by(template=template)
                conc = await session.scalar(stmt)
                if not conc:
                    conc = ConceptTable(template=template)
                    if category:
                        cat = await self.ensure_category(session, category.value)
                        conc.category_id = cat.id
                    session.add(conc)
                elif category and conc.category_id is None:
                    cat = await self.ensure_category(session, category.value)
                    conc.category_id = cat.id
                
                results.append(conc)
            await session.commit()
        return results

    async def ensure_category(self, session, category_text: str):
        return await self._get_or_create(session, Category, text=category_text)

    async def populate_categories(self):
        """Populate the categories table with predefined categories."""
        category_names = [cat.value for cat in CategoryEnum]
        
        async_session = async_sessionmaker(self.log_engine, expire_on_commit=False)
        async with async_session() as session:
            for cat_name in category_names:
                await self.ensure_category(session, cat_name)
            await session.commit()

    async def add_constants(self):
        async_session = async_sessionmaker(self.engine, expire_on_commit=False)

        async with async_session() as session:
            # Rulesets
    
            # ruleset_stmt = await session.stream(select(Ruleset.id))
            # rulesets_in_db = list(await ruleset_stmt.fetchall())

            ruleset_stmt = select(Ruleset.id)
            rulesets_in_db = list(await session.scalars(ruleset_stmt))
            for ruleset_id, ruleset_name in enumerate(['Standard', 'Cheese', 'Survivor', 'Slowest Link', '40 Lines']):
                if ruleset_id in rulesets_in_db:
                    continue

                session.add(
                    Ruleset(
                        id = ruleset_id,
                        name = ruleset_name
                    )
                )

            # Teams    

            # team_stmt = await session.stream(select(Team.id))
            # teams_in_db = list(await team_stmt.fetchall())
            
            team_stmt = select(Team.id)
            teams_in_db = list(await session.scalars(team_stmt))

            for team_id, team_name in enumerate(['Red', 'Blue', 'Green', 'Yellow']):
                if team_id in teams_in_db:
                    continue

                session.add(
                    Team(
                        id = team_id,
                        name = team_name
                    )
                )


            await session.commit()
            


    async def update_achievements(self):
        achievements = await Endpoint.achievements()
        if achievements.has_error():
            return None
        
        api_achievements = achievements.data.keys()

        async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        

        # Check if there are achievements in API response that are not in DB, and add them to the DB if it's the case
        async with async_session() as session:
            db_achievements_stmt = await session.stream(select(Achievement.name, Achievement.count))

            db_achievements =  {name: count for name, count in await db_achievements_stmt.fetchall()}

            for achievement_name in api_achievements:
                achievement = Achievement(
                    name        = achievement_name,
                    title       = achievements.data.get(achievement_name).get("title"),
                    description = achievements.data.get(achievement_name).get("description"),
                    is_public   = achievements.data.get(achievement_name).get("isPublic"),
                    points      = achievements.data.get(achievement_name).get("points"),
                    count       = achievements.data.get(achievement_name).get("count")
                )
                if achievement_name in db_achievements.keys():
                    if achievement.count != db_achievements.get(achievement_name):
                        await session.merge(achievement)
                        db_achievements.pop(achievement_name)
                else:
                    session.add(achievement)

            # deal with unused achievements TODO
            await session.commit()
            

    async def update_user(self, user_id: int, last_played: datetime | None = None):
        """Fetch a user from the API and insert/update the Users table.

        If `last_played` is provided, update the user's `last_played` if it's
        newer than the stored value. Peak rank/score fields are updated when
        the new values exceed stored peaks; peak dates are set to current UTC.
        """
        api_response = await Endpoint.user(user_id)
        if api_response.has_error():
            return None

        data = api_response.data
        stats = data.get('stats', {}) or {}

        # parse creation date if present
        creation_date = None
        if data.get('created'):
            try:
                creation_date = datetime.fromisoformat(data.get('created'))
            except Exception:
                creation_date = None

        rank = stats.get('rank')
        score = stats.get('score')
        max_combo = stats.get('maxCombo') or 0
        max_bpm = stats.get('maxroundBpm') or 0
        avg_bpm = stats.get('avgroundBpm') or 0

        async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with async_session() as session:
            existing = await session.get(User, user_id)
            now_utc = datetime.now(timezone.utc)

            if existing:
                # Track name changes
                old_name = existing.name
                new_name = data.get('name')
                existing.name = new_name
                
                # Track rank changes for netscore
                rank_before = existing.rank
                score_before = existing.score
                
                if rank is not None:
                    existing.rank = rank
                    if existing.peak_rank is None or rank > existing.peak_rank:
                        existing.peak_rank = rank
                        existing.peak_rank_date = now_utc

                if score is not None:
                    existing.score = score
                    if existing.peak_score is None or score > existing.peak_score:
                        existing.peak_score = score
                        existing.peak_score_date = now_utc
                
                # Record netscore if rank or score changed
                if (rank_before != rank) or (score_before != score):
                    netscore = Netscore(
                        timestamp=now_utc,
                        user_id=user_id,
                        rank_before=rank_before,
                        rank_after=rank,
                        score_before=score_before,
                        score_after=score
                    )
                    session.add(netscore)

                # Log name change if name changed
                if old_name != new_name:
                    try:
                        self.log_event_async(
                            "update_user",
                            Concept.NameChange,
                            text_params=[old_name, new_name],
                        )
                    except Exception:
                        # logging should not interrupt main flow
                        pass

                # log the update or creation of a user
                try:
                    self.log_event_async(
                        "update_user",
                        Concept.UpdateUser,
                        text_params=[data.get('name')],
                        num_params=[user_id],
                    )
                except Exception:
                    # logging should not interrupt main flow
                    pass

                if last_played:
                    # prefer the newest last_played
                    try:
                        if existing.last_played is None or existing.last_played < last_played:
                            existing.last_played = last_played
                    except Exception:
                        existing.last_played = last_played

                session.add(existing)
                await session.commit()
                return existing
            else:
                user = User(
                    id = data.get('userId'),
                    name = data.get('name'),
                    rank = rank,
                    score = score,
                    max_combo = max_combo,
                    max_bpm = max_bpm,
                    avg_bpm = avg_bpm,
                    creation_date = creation_date,
                    last_played = last_played
                )

                # set peaks on initial insert
                if rank is not None:
                    user.peak_rank = rank
                    user.peak_rank_date = now_utc
                if score is not None:
                    user.peak_score = score
                    user.peak_score_date = now_utc

                session.add(user)
                await session.commit()
                # record creation (non-blocking)
                try:
                    self.log_event_async(
                        "update_user",
                        Concept.CreateUser,
                        text_params=[data.get('name')],
                        num_params=[user_id],
                    )
                except Exception:
                    pass
                return user

    async def update_rankings(self):
        """Recalculate all user ranks based solely on their current score.

        Users are sorted by ``score`` in descending order (highest first).
        The user with the greatest score receives rank ``1``, the next
        highest score receives rank ``2``, etc.  Accounts whose ``score`` is
        ``None`` will have ``rank`` cleared to ``None`` as well.

        This method uses the ORM rather than custom SQL so it works with the
        same session management used elsewhere in :class:`Database`.
        """
        async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with async_session() as session:
            # order users by score descending, placing NULLs last
            stmt = select(User).order_by(User.score.desc().nulls_last())
            users = await session.scalars(stmt)

            current_rank = 1
            for user in users:
                if user.score is None:
                    user.rank = None
                else:
                    user.rank = current_rank
                    current_rank += 1
                session.add(user)
            await session.commit()

    async def get_last_user_id(self) -> int:
        """Get the maximum user ID in the Users table, or 0 if the table is empty."""
        async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with async_session() as session:
            result = await session.scalar(select(func.max(User.id)))
            return result or 0

    async def get_last_round_id(self) -> int:
        """Get the maximum round ID in the Rounds table, or 0 if the table is empty."""
        async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with async_session() as session:
            result = await session.scalar(select(func.max(Round.round_id)))
            return result or 0

    async def get_users_with_rank_below(self, threshold: int) -> list[int]:
        """Get all user IDs with rank less than or equal to the given threshold.

        Returns a list of user IDs sorted by rank (ascending).
        """
        async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with async_session() as session:
            stmt = select(User.id).where(
                User.rank <= threshold
            ).order_by(User.rank.asc())
            user_ids = await session.scalars(stmt)
            return list(user_ids)

    async def commit(self):
        """Commit any pending changes to both stats and logging databases.

        This ensures that any uncommitted transactions are flushed and committed
        to disk. Typically called after a series of operations that should be
        atomically saved together.
        """
        try:
            async with self.engine.begin() as conn:
                await conn.commit()
        except Exception as e:
            logging.error(f"Failed to commit stats database changes: {e}")
            raise

        try:
            async with self.log_engine.begin() as conn:
                await conn.commit()
        except Exception as e:
            logging.error(f"Failed to commit log database changes: {e}")
            raise

    async def process_next_round_batch(self, update_players = False) -> int:
        """Fetch and process the next batch of rounds (up to 1000).

        Automatically determines the starting round ID based on what's already
        stored in the database, fetches the next batch (up to 1000 rounds),
        aggregates played round statistics, and recalculates user rankings.

        Returns the number of rounds added in this batch (0 if no new rounds).
        """
        last_round_id = await self.get_last_round_id()
        next_start = last_round_id + 1

        rounds_added = await self.add_rounds(next_start, update_players=update_players)

        if rounds_added and rounds_added > 0:
            await self.process_rounds(next_start, next_start + rounds_added - 1)

        return rounds_added or 0

    async def update_userlist(self, start_id: int, end_id: int | None = None):
        """Iterate calls to :meth:`update_user` over a range of user IDs.

        *start_id* defines the first user ID to request.  If *end_id* is
        provided iteration stops when the current ID exceeds it.  When
        *end_id* is ``None`` the method will continue fetching sequential
        IDs until it believes there are no more users – this is detected by
        encountering three consecutive missing users (``update_user`` returns
        ``None``).

        Holes are expected so a few misses are tolerated before termination.

        When an ID fails to fetch from the API, a placeholder row is inserted
        into the Users table with just the ID and no name, ensuring every
        checked ID has a corresponding row.

        Returns the number of successful updates performed.
        """
        current = start_id
        misses = 0
        updated = 0

        while True:
            if end_id is not None and current > end_id:
                break

            user = await self.update_user(current)
            if user is None:
                # no user at this ID from API; insert a placeholder row
                async_session = async_sessionmaker(self.engine, expire_on_commit=False)
                async with async_session() as session:
                    existing = await session.get(User, current)
                    if not existing:
                        placeholder = User(id=current)
                        session.add(placeholder)
                        await session.commit()
                misses += 1
            else:
                misses = 0
                updated += 1

            if end_id is None and misses >= 3:
                # assume we've walked past the last existing user
                break

            current += 1

        return updated


    async def add_rounds(self, start_id: int, update_players: bool = False):
        """Fetch up to 1000 matches starting from `start_id`, bulk insert Matches and Rounds.

        If `update_players` is True, call `update_user` for each player with a valid userId.
        Uses bulk_insert_mappings for significantly faster insertion performance.
        """
        api_response = await Endpoint.rounds(start_id)
        if api_response.has_error():
            return None

        matches = api_response.data or []
        if not matches: 
            return 0

        # matches = convert_rounds_range(start_id, start_id + 50000)

        # Collect match and round data for bulk insertion
        matches_data = []
        rounds_data = []
        user_updates = []

        for match in matches:
            match_id = match.get('roundId')

            # parse start timestamp
            start_dt = None
            if match.get('start'):
                try:
                    start_dt = datetime.fromisoformat(match.get('start').replace('Z', '+00:00'))
                except Exception:
                    start_dt = None

            # infer roomsize from number of players
            players = match.get('players', []) or []
            roomsize = len(players)

            # Collect match data
            matches_data.append({
                'id': match_id,
                'start': start_dt,
                'ruleset': str(match.get('ruleset')) if match.get('ruleset') is not None else None,
                'is_official': match.get('isOfficial'),
                'speedlimit': match.get('speedLimit'),
                'roomsize': roomsize
            })

            for idx, player in enumerate(players):
                user_id = player.get('userId')
                if user_id == -1:
                    user_val = None
                else:
                    user_val = user_id

                # place is inferred from order
                place = idx + 1

                # Collect round data
                rounds_data.append({
                    'round_id': match_id,
                    'user_id': user_val,
                    'guest_name': player.get('guestName'),
                    'place': place,
                    'lines_got': player.get('linesGot'),
                    'lines_sent': player.get('linesSent'),
                    'lines_blocked': player.get('linesBlocked'),
                    'max_combo': player.get('maxCombo'),
                    'blocks': player.get('blocks'),
                    'play_duration': player.get('playDuration'),
                    'team': player.get('team'),
                    'cheese_rows': player.get('cheeseRows')
                })

                # Collect user updates to process after bulk insert
                if update_players and user_val is not None and match.get('isOfficial'):
                    user_updates.append((user_val, start_dt))

        # Perform bulk inserts using async session
        async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with async_session() as session:
            # Bulk insert matches
            if matches_data:
                await session.run_sync(
                    lambda sync_session: sync_session.bulk_insert_mappings(Match, matches_data)
                )

            # Bulk insert rounds
            if rounds_data:
                await session.run_sync(
                    lambda sync_session: sync_session.bulk_insert_mappings(Round, rounds_data)
                )

            await session.commit()

        # Process user updates after bulk insert (non-blocking to maintain performance)
        if user_updates:
            # Retransfcorn user_updates into user_updates_unique where we just have one element per user, with its largest dt for last played
            user_updates_unique = []
            unique_users = {user_id for user_id, _ in user_updates}
            for unique_user in unique_users:
                max_dt = max([dt for user_id, dt in user_updates if user_id == unique_user])
                user_updates_unique.append((unique_user, max_dt))
                
            for user_id, last_played in user_updates_unique:
                try:
                    await self.update_user(user_id, last_played=last_played)
                except Exception:
                    # don't fail the whole import if a single user update fails
                    logging.exception(f"Failed to update user {user_id}")

        # log the addition of rounds once at the end
        try:
            self.log_event_async(
                "add_rounds",
                Concept.AddRound,
                num_params=[start_id, start_id + len(matches) - 1],
            )
        except Exception:
            pass

        return len(matches)
    
    async def process_rounds(self, min_round_id: int | None = None, max_round_id: int | None = None):
        """Aggregate existing Rounds rows into UserCombos and UserPlayedRounds.

        If `min_round_id` or `max_round_id` are provided the method will only
        operate on rounds whose `roundId` lies within the inclusive range.
        This allows post-processing a subset of newly-imported records.

        The aggregation adds values to the target tables rather than recomputing
        from scratch; calling twice on the same range will double-count, so only
        pass fresh ranges or ensure idempotency externally.
        """
        async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        async with async_session() as session:
            # precompute the number of players in each round within the window
            sizes = {}
            size_stmt = select(Round.round_id, func.count()).group_by(Round.round_id)
            if min_round_id is not None:
                size_stmt = size_stmt.where(Round.round_id >= min_round_id)
            if max_round_id is not None:
                size_stmt = size_stmt.where(Round.round_id <= max_round_id)
            for rid, cnt in await session.execute(size_stmt):
                sizes[rid] = cnt

            now_utc = datetime.now(timezone.utc)
            combo_cache: dict[tuple[int, int, int], UserCombo] = {}
            played_cache: dict[tuple[int, int], UserPlayedRound] = {}

            stmt = select(Round, Match.ruleset, Match.start).join(Match, Round.round_id == Match.id)
            if min_round_id is not None:
                stmt = stmt.where(Round.round_id >= min_round_id)
            if max_round_id is not None:
                stmt = stmt.where(Round.round_id <= max_round_id)

            result = await session.execute(stmt)
            for round_obj, ruleset, match_start in result:
                round_obj: Round
                user_id = round_obj.user_id
                # prefer the match start time for timestamps, fallback to now
                ts = match_start if match_start is not None else datetime.now(timezone.utc)
                # guests have id -1; skip them (also skip None just in case)
                if user_id is None or user_id == -1:
                    continue

                # track combo
                combo_key = (user_id, ruleset, round_obj.max_combo)
                uc = combo_cache.get(combo_key)
                if uc is None:
                    uc = await session.scalar(
                        select(UserCombo).where(
                            UserCombo.user_id == user_id,
                            UserCombo.ruleset == ruleset,
                            UserCombo.combo == round_obj.max_combo,
                        )
                    )
                    if uc is None:
                        uc = UserCombo(
                            user_id=user_id,
                            ruleset=ruleset,
                            combo=round_obj.max_combo,
                            count=0,
                            count_alone=0,
                            created_at=ts,
                            updated_at=ts,
                        )
                        session.add(uc)
                    combo_cache[combo_key] = uc

                uc.count += 1
                if sizes.get(round_obj.round_id, 0) <= 1:
                    uc.count_alone += 1
                uc.updated_at = ts

                # aggregate played rounds stats
                play_key = (user_id, ruleset)
                upr = played_cache.get(play_key)
                if upr is None:
                    upr = await session.scalar(
                        select(UserPlayedRound).where(
                            UserPlayedRound.user_id == user_id,
                            UserPlayedRound.ruleset == ruleset,
                        )
                    )
                    if upr is None:
                        upr = UserPlayedRound(
                            user_id=user_id,
                            ruleset=ruleset,
                            played_rounds=0,
                            place=0,
                            roomsize=0,
                            lines_got=0,
                            lines_sent=0,
                            lines_blocked=0,
                            blocks=0,
                            played_time=0.0,
                            played_time_teams=0.0,
                            created_at=ts,
                            updated_at=ts,
                        )
                        session.add(upr)
                    played_cache[play_key] = upr

                upr.played_rounds += 1
                upr.place += round_obj.place or 0
                upr.roomsize += sizes.get(round_obj.round_id, 0)
                upr.lines_got += round_obj.lines_got or 0
                upr.lines_sent += round_obj.lines_sent or 0
                upr.lines_blocked += round_obj.lines_blocked or 0
                upr.blocks += round_obj.blocks or 0
                upr.played_time += round_obj.play_duration or 0.0
                if round_obj.team is not None:
                    upr.played_time_teams += round_obj.play_duration or 0.0
                # update last-modified timestamp for aggregations
                upr.updated_at = ts

            await session.commit()

        # log range processed (nil means unrestricted) - non-blocking
        try:
            if min_round_id is not None or max_round_id is not None:
                self.log_event_async(
                    "process_rounds",
                    Concept.ProcessRounds,
                    num_params=[min_round_id or 0, max_round_id or 0],
                )
            else:
                self.log_event_async(
                    "process_rounds",
                    Concept.ProcessAllRounds,
                )
        except Exception:
            pass

if __name__ == '__main__':
    async def main():
        try:
            # pass both stats and log database paths; log file may share or be
            # distinct from the stats database.
            db = await Database.connect('files/cultris2.db', 'files/log.db')
            # result = await db.add_rounds(13416046)
            # await db.add_constants()
            # await db.process_rounds(13416046, 13417046)
            # await db.process_rounds(13341002, 13341002 + 1000)
            # _added = await db.process_next_round_batch()

            start = perf_counter()

            rounds_added = 1 
            continue_ = True

            while rounds_added and continue_:
                rounds_added = await db.process_next_round_batch()
                last_round_id = await db.get_last_round_id()
                print(last_round_id)

                with open('database/safeend') as f:
                    l = f.read()
                    if l == '1': continue_ = False
                    

            print(perf_counter() - start)

            # await db.update_userlist(40001, 47434)
            # r = await db.add_rounds(1)
            # await db.add_rounds(1002)
            
            # print(result)
            # dispose engine connections so that asyncio loop can close cleanly
        except:
            print(traceback.format_exc())
        finally:
            await db.engine.dispose()
            await db.log_engine.dispose()

    asyncio.run(main())
