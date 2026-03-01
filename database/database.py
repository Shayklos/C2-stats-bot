import asyncio
from sqlalchemy import text
from sqlalchemy import func
from sqlalchemy import select
import sqlalchemy.ext.asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import traceback
from os.path import join
import sys
import logging

from Endpoint import Endpoint
from models.UserPlayedRound import UserPlayedRound
from models.UserCombo import UserCombo
from models.User import User
from models.Achievement import Achievement
from datetime import datetime, timezone
from models.Match import Match
from models.Round import Round
from models.Team import Team
from models.Ruleset import Ruleset

class Base(DeclarativeBase):
    pass

class Database:
    def __init__(self, engine: sqlalchemy.ext.asyncio.AsyncEngine):
        self.engine = engine

    @classmethod
    async def connect(cls, db_filepath):
        engine = sqlalchemy.ext.asyncio.create_async_engine("sqlite+aiosqlite:///" + db_filepath, echo = True)
    
        async with engine.begin() as conn:
           await conn.run_sync(Base.metadata.create_all)
        
        return Database(engine)

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
                existing.name = data.get('name')
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

                existing.max_combo = max_combo
                existing.max_bpm = max_bpm
                existing.avg_bpm = avg_bpm
                if creation_date:
                    existing.creation_date = creation_date

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
                return user


    async def add_rounds(self, start_id: int, update_players: bool = False):
        """Fetch up to 1000 matches starting from `start_id`, insert Matches and Rounds.

        If `update_players` is True, call `update_user` for each player with a valid userId.
        """
        api_response = await Endpoint.rounds(start_id)
        if api_response.has_error():
            return None

        matches = api_response.data or []

        async_session = async_sessionmaker(self.engine, expire_on_commit=False)

        async with async_session() as session:
            for match in matches:
                match_id = match.get('roundId')

                # parse start timestamp
                start_dt = None
                if match.get('start'):
                    try:
                        start_dt = datetime.fromisoformat(match.get('start').replace('Z', '+00:00'))
                    except Exception:
                        start_dt = None

                match_obj = Match(
                    id = match_id,
                    start = start_dt,
                    ruleset = str(match.get('ruleset')) if match.get('ruleset') is not None else None,
                    is_official = match.get('isOfficial'),
                    speedlimit = match.get('speedLimit')
                )

                # upsert match
                await session.merge(match_obj)

                players = match.get('players', []) or []
                for idx, player in enumerate(players):
                    user_id = player.get('userId')
                    if user_id == -1:
                        user_val = None
                    else:
                        user_val = user_id

                    # place is inferred from order
                    place = idx + 1

                    # skip if this round for this user already exists (simple dedup)
                    exists_stmt = select(Round).where(
                        Round.round_id == match_id,
                        Round.user_id == user_val
                    )
                    existing_round = await session.scalar(exists_stmt)
                    if existing_round is not None:
                        # already stored, skip insertion and user update
                        continue

                    round_obj = Round(
                        round_id = match_id,
                        user_id = user_val,
                        guest_name = player.get('guestName'),
                        place = place,
                        lines_got = player.get('linesGot'),
                        lines_sent = player.get('linesSent'),
                        lines_blocked = player.get('linesBlocked'),
                        max_combo = player.get('maxCombo'),
                        blocks = player.get('blocks'),
                        play_duration = player.get('playDuration'),
                        team = player.get('team'),
                        cheese_rows = player.get('cheeseRows')
                    )

                    # add round
                    session.add(round_obj)

                    # optionally update player/user record
                    if update_players and user_val is not None:
                        try:
                            await self.update_user(user_val, last_played=start_dt)
                        except Exception:
                            # don't fail the whole import if a single user update fails
                            logging.exception(f"Failed to update user {user_val}")

            await session.commit()

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

        return True   

if __name__ == '__main__':
    async def main():
        try:
            db = await Database.connect('files/cultris2.db')
            # result = await db.add_rounds(13416046)
            # await db.add_constants()
            await db.process_rounds(13416046, 13417046)
            # print(result)
            # dispose engine connections so that asyncio loop can close cleanly
        except:
            # print("ERROR")
            print(traceback.format_exc())
        finally:
            await db.engine.dispose()

    asyncio.run(main())
