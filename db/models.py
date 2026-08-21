from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class ResearchRun(Base):
    """
    SQLAlchemy model for persisting research workflow executions and final reports.
    """
    __tablename__ = "research_runs"

    run_id = Column(String(64), primary_key=True, index=True)
    question = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    total_tokens = Column(Integer, default=0)
    total_searches = Column(Integer, default=0)
    revision_count = Column(Integer, default=0)
    execution_time_sec = Column(Float, default=0.0)
    
    # Final Structured Report Fields
    report_title = Column(Text, nullable=True)
    report_summary = Column(Text, nullable=True)
    report_data = Column(JSON, nullable=True)
    citations = Column(JSON, nullable=True)
    validation_warnings = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    trace_steps = relationship("TraceStep", back_populates="run", cascade="all, delete-orphan")

class TraceStep(Base):
    """
    SQLAlchemy model for permanent audit trail of every agent action and tool call.
    """
    __tablename__ = "trace_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False, default=1)
    agent_name = Column(String(64), nullable=False, index=True)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    tools_called = Column(JSON, nullable=True)
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    run = relationship("ResearchRun", back_populates="trace_steps")
