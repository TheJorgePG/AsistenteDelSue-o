from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.core.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    display_name = Column(String(60), nullable=False)
    age_range = Column(String(20), nullable=False)
    sleep_goal_hours = Column(Float, nullable=False, default=8.0)
    timezone = Column(String(64), nullable=False, default="UTC")
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now
    )


class DailySleepLogModel(Base):
    __tablename__ = "daily_sleep_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "sleep_date", name="uq_daily_sleep_user_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sleep_date = Column(Date, nullable=False)
    hours_slept = Column(Float, nullable=False)
    quality_score = Column(Integer, nullable=False)
    awakenings = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
