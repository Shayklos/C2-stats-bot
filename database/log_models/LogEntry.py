from sqlalchemy import Column, Integer, Text, Numeric, ForeignKey, DateTime
from datetime import datetime, timezone
from .Base import LogBase as Base

class LogEntry(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    function_id = Column(Integer, ForeignKey("functions.id"), nullable=False)
    concept_id = Column(Integer, ForeignKey("concepts.id"), nullable=False)

    # record when the event was logged (UTC)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    param1_text = Column(Text, nullable=True)
    param2_text = Column(Text, nullable=True)
    param3_text = Column(Text, nullable=True)

    param1_num = Column(Numeric, nullable=True)
    param2_num = Column(Numeric, nullable=True)
    param3_num = Column(Numeric, nullable=True)

    def __repr__(self):
        return (
            f"<LogEntry(id={self.id}, function_id={self.function_id}, "
            f"concept_id={self.concept_id}, timestamp={self.timestamp})>"
        )
