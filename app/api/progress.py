from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.security import get_current_user
from app.core.database import get_db
from app.models.progress import DailySleepLogModel, UserProfileModel
from app.models.user import UserModel
from app.services.progress import build_dashboard, serialize_profile, serialize_sleep_log
from app.services.progress_report import create_progress_pdf


router = APIRouter(tags=["Progreso personal"])


class ProfileInput(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=60)
    age_range: Literal["18-25", "26-64", "65+"]
    sleep_goal_hours: float = Field(..., ge=4, le=12)
    timezone: str = Field(..., min_length=1, max_length=64)

    @field_validator("display_name")
    @classmethod
    def display_name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre no puede estar vacío.")
        return value

    @field_validator("timezone")
    @classmethod
    def timezone_must_be_valid(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Indica una zona horaria IANA válida.") from error
        return value


class SleepLogInput(BaseModel):
    sleep_date: date
    hours_slept: float = Field(..., gt=0, le=24)
    quality_score: int = Field(..., ge=1, le=10)
    awakenings: int = Field(default=0, ge=0, le=30)


def _load_profile(db: Session, user_id: int) -> UserProfileModel | None:
    return (
        db.query(UserProfileModel)
        .filter(UserProfileModel.user_id == user_id)
        .first()
    )


def _load_logs(db: Session, user_id: int) -> list[DailySleepLogModel]:
    return (
        db.query(DailySleepLogModel)
        .filter(DailySleepLogModel.user_id == user_id)
        .order_by(DailySleepLogModel.sleep_date.asc())
        .all()
    )


@router.get("/profile")
def read_profile(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"profile": serialize_profile(_load_profile(db, user.id))}


@router.put("/profile")
def update_profile(
    payload: ProfileInput,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _load_profile(db, user.id)
    if profile is None:
        profile = UserProfileModel(user_id=user.id)
        db.add(profile)

    profile.display_name = payload.display_name
    profile.age_range = payload.age_range
    profile.sleep_goal_hours = payload.sleep_goal_hours
    profile.timezone = payload.timezone
    db.commit()
    db.refresh(profile)
    return {"profile": serialize_profile(profile)}


@router.get("/progress")
def read_progress(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _load_profile(db, user.id)
    logs = _load_logs(db, user.id)
    return build_dashboard(profile, logs)


@router.post("/sleep-logs", status_code=status.HTTP_201_CREATED)
def create_sleep_log(
    payload: SleepLogInput,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _load_profile(db, user.id)
    local_today = datetime.now(ZoneInfo(profile.timezone if profile else "UTC")).date()
    if payload.sleep_date > local_today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La fecha del registro no puede ser futura.",
        )

    existing = (
        db.query(DailySleepLogModel)
        .filter(
            DailySleepLogModel.user_id == user.id,
            DailySleepLogModel.sleep_date == payload.sleep_date,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un registro para esa fecha.",
        )

    log = DailySleepLogModel(
        user_id=user.id,
        sleep_date=payload.sleep_date,
        hours_slept=payload.hours_slept,
        quality_score=payload.quality_score,
        awakenings=payload.awakenings,
    )
    db.add(log)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un registro para esa fecha.",
        ) from error
    db.refresh(log)
    return {"sleep_log": serialize_sleep_log(log)}


@router.get("/reports/progress.pdf")
def download_progress_report(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _load_profile(db, user.id)
    logs = _load_logs(db, user.id)
    report = create_progress_pdf(profile, logs)
    return Response(
        content=report,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="mi-progreso-sueno.pdf"'},
    )
