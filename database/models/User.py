from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from models.Base import Base
from datetime import datetime

class User(Base):
    __tablename__ = "Users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255, collation='NOCASE'))
    rank: Mapped[Optional[int]]
    score: Mapped[Optional[int]]
    max_combo: Mapped[int] = mapped_column(Integer, default = 0, name = "maxCombo")
    max_bpm: Mapped[float] = mapped_column(Float, default = 0, name = "maxBPM")
    avg_bpm: Mapped[float] = mapped_column(Integer, default = 0, name = "avgBPM")
    peak_rank: Mapped[Optional[int]] = mapped_column(name = 'peakRank')
    peak_score: Mapped[Optional[int]] = mapped_column(name = 'peakScore')
    last_played: Mapped[Optional[datetime]] = mapped_column(name = 'lastPlayed')
    last_login: Mapped[Optional[datetime]] = mapped_column(name = 'lastLogin')
    creation_date: Mapped[datetime] = mapped_column(name = 'creationDate')
    peak_rank_date: Mapped[Optional[datetime]] = mapped_column(name = 'peakRankDate')
    peak_score_date: Mapped[Optional[datetime]] = mapped_column(name = 'peakScoreDate')

    
    def __repr__(self) -> str:
        return f"User(id={self.id}, name={self.name})"