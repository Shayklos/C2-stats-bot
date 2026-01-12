from datetime import datetime
from models import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

class Match(Base):
    __tablename__ = "Matches"
    id: Mapped[int] = mapped_column(primary_key=True)
    start: Mapped[datetime]
    ruleset: Mapped[str] = mapped_column(String(32))
    is_official: Mapped[bool] = mapped_column(name='isOfficial')
    speedlimit: Mapped[int]