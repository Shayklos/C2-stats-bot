from sqlalchemy import Column, Integer, String
from .Base import LogBase as Base

class Function(Base):
    __tablename__ = "functions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    def __repr__(self):
        return f"<Function(id={self.id}, name={self.name})>"
