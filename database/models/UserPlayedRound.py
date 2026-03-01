from datetime import datetime
from models.Base import Base
from models.User import User
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

"""
Table that keeps track of global stats
"""
class UserPlayedRound(Base):
    __tablename__ = "UserPlayedRounds"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True) 
    user_id: Mapped[int] = mapped_column(ForeignKey("Users.id"), name='userId')
    ruleset: Mapped[int] = mapped_column(ForeignKey("Rulesets.id"))
    played_rounds: Mapped[int] = mapped_column(Integer, name = "playedRounds") 
    place: Mapped[int]
    roomsize: Mapped[int]
    lines_got: Mapped[int] = mapped_column(name = 'linesGot')
    lines_sent: Mapped[int] = mapped_column(name = 'linesSent')
    lines_blocked: Mapped[int] = mapped_column(name = 'linesBlocked')
    blocks: Mapped[int]
    played_time: Mapped[float] = mapped_column(name='playedTime')
    played_time_teams: Mapped[float] = mapped_column(name='playedTimeTeams')
    created_at: Mapped[datetime] = mapped_column(name = 'createdAt')
    updated_at: Mapped[datetime] = mapped_column(name = 'updatedAt')