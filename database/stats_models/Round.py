from datetime import datetime
from typing import Optional
from .Base import Base
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Round(Base):
    __tablename__ = "Rounds"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(ForeignKey('Matches.id'), name='roundId')
    user_id: Mapped[int] = mapped_column(ForeignKey('Users.id'), name='userId', nullable = True)
    guest_name: Mapped[str] = mapped_column(name='guestName')
    place: Mapped[int]
    lines_got: Mapped[int] = mapped_column(name='linesGot')
    lines_sent: Mapped[int] = mapped_column(name='linesSent')
    lines_blocked: Mapped[int] = mapped_column(name='linesBlocked')
    max_combo: Mapped[int] = mapped_column(name='maxCombo')
    blocks: Mapped[int]
    play_duration: Mapped[float] = mapped_column(name = 'playDuration')
    team: Mapped[int] = mapped_column(ForeignKey('Teams.id'), nullable = True)
    cheese_rows: Mapped[int] = mapped_column(name='cheeseRows')
    