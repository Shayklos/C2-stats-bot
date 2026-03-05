from sqlalchemy import Column, Integer, String
from .Base import LogBase as Base

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, unique=True, nullable=False)

    def __repr__(self):
        return f"<Category(id={self.id}, text={self.text})>"
