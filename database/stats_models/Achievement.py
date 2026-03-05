from .Base import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

class Achievement(Base):
    __tablename__ = "Achievements"
    name: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str]
    is_public: Mapped[bool] = mapped_column(name = 'isPublic')
    points: Mapped[int]
    count: Mapped[int]