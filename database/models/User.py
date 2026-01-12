from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from models import Base
from datetime import datetime

class User(Base):
    __tablename__ = "Users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255, collation='NOCASE'))
    rank: Mapped[int] = mapped_column(Optional[Integer])
    score: Mapped[int] = mapped_column(Optional[Float])
    max_combo: Mapped[int] = mapped_column(Integer, default = 0, name = "maxCombo")
    max_bpm: Mapped[float] = mapped_column(Float, default = 0, name = "maxBPM")
    avg_bpm: Mapped[float] = mapped_column(Integer, default = 0, name = "avgBPM")
    peak_rank: Mapped[int] = mapped_column(Optional[Integer], name = 'peakRank')
    peak_score: Mapped[int] = mapped_column(Optional[Float], name = 'peakScore')
    last_played: Mapped[Optional[datetime]]
    last_login: Mapped[Optional[datetime]]
    creation_date: Mapped[datetime]
    peak_rank_date: Mapped[Optional[datetime]]

    
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"