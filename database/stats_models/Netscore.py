from sqlalchemy import Column, Integer, DateTime, ForeignKey
from datetime import datetime, timezone
from .Base import Base


class Netscore(Base):
    __tablename__ = "Netscores"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    rank_before = Column(Integer, nullable=True)
    rank_after = Column(Integer, nullable=True)
    score_before = Column(Integer, nullable=True)
    score_after = Column(Integer, nullable=True)

    def __repr__(self):
        return (
            f"<Netscore(id={self.id}, timestamp={self.timestamp}, user_id={self.user_id}, "
            f"rank_before={self.rank_before}, rank_after={self.rank_after}, "
            f"score_before={self.score_before}, score_after={self.score_after})>"
        )
