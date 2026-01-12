from datetime import datetime
from models import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

"""
Table that keeps track of how many combo of each for each ruleset each user has
"""
class UserCombo(Base):
    __tablename__ = "UserCombos"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("Users.userId"), name='userId')
    ruleset: Mapped[int] = mapped_column(ForeignKey("Rulesets.id"))
    combo: Mapped[int]
    count: Mapped[int]
    count_alone: Mapped[int] = mapped_column(name = "countAlone") # how many of Count have been made against no players
    created_at: Mapped[datetime] = mapped_column(name = 'createdAt')
    updated_at: Mapped[datetime] = mapped_column(name = 'updatedAt')