"""
SQLAlchemy models.

One HCP interaction "draft" per chat session. The record is created the
moment the Log Interaction tool first runs, and updated in place by the
Edit Interaction / Search Add Material / Log Sample Distribution /
Suggest Follow Up tools.
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String(64), unique=True, index=True, nullable=False)

    hcp_name = Column(String(255), nullable=True)
    interaction_type = Column(String(64), nullable=True, default="Meeting")
    date = Column(String(32), nullable=True)
    time = Column(String(32), nullable=True)
    attendees = Column(JSON, default=list)

    topics_discussed = Column(Text, nullable=True)

    materials_shared = Column(JSON, default=list)
    samples_distributed = Column(JSON, default=list)

    sentiment = Column(String(32), nullable=True)
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    compliance_flag = Column(Text, nullable=True)

    logged = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "hcp_name": self.hcp_name,
            "interaction_type": self.interaction_type,
            "date": self.date,
            "time": self.time,
            "attendees": self.attendees or [],
            "topics_discussed": self.topics_discussed,
            "materials_shared": self.materials_shared or [],
            "samples_distributed": self.samples_distributed or [],
            "sentiment": self.sentiment,
            "outcomes": self.outcomes,
            "follow_up_actions": self.follow_up_actions,
            "compliance_flag": self.compliance_flag,
            "logged": self.logged,
        }