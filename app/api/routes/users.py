from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.repository.database import get_db
from app.repository.models import Game, Participant
from app.schemas.user import NicknameCheckResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/check-nickname", response_model=NicknameCheckResponse)
def check_nickname(
    nickname: str = Query(..., description="확인할 닉네임"),
    db: Session = Depends(get_db),
):
    """닉네임 중복 확인 — 진행 중인 게임(PREGAME/INGAME) 기준"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    exists = (
        db.query(Participant)
        .join(Game)
        .filter(
            Participant.nickname == nickname,
            or_(Game.ended_at.is_(None), Game.ended_at > now),
        )
        .first()
    )
    if exists:
        return JSONResponse(
            status_code=409,
            content={"message": "이미 사용 중인 닉네임입니다."},
        )
    return NicknameCheckResponse(isDuplicate=False)
