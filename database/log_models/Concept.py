from sqlalchemy import Column, Integer, Text, ForeignKey
from .Base import LogBase as Base

class Concept(Base):
    __tablename__ = "concepts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template = Column(Text, unique=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    def __repr__(self):
        return f"<Concept(id={self.id}, template={self.template}, category_id={self.category_id})>"
