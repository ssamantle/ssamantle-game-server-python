from datetime import datetime, timezone

import redis
from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from starlette.requests import Request

from app.repository.enums import GameStatus
from app.repository.models import Game, Participant
from app.repository.redis.client import get_redis_client
from app.repository.vector import VectorDB, get_vector_db as get_repository_vector_db
from app.schemas.game import LeaderboardEntry
from app.utils import build_submission_detail, get_best_guess, get_latest_guess


def get_vector_db() -> VectorDB:
    try:
        return get_repository_vector_db()
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="벡터 데이터베이스를 찾을 수 없습니다.",
        ) from error


def get_redis() -> redis.Redis:
    try:
        client = get_redis_client()
        client.ping()
        return client
    except redis.exceptions.ConnectionError as error:
        raise HTTPException(
            status_code=503,
            detail="Redis에 연결할 수 없습니다.",
        ) from error


def get_session(request: Request) -> dict:
    if not request.session.get("nickname"):
        raise HTTPException(status_code=401, detail="인증되지 않은 사용자입니다.")
    return request.session


def get_host_session(request: Request, game_id: int) -> dict:
    session = get_session(request)
    if not session.get("is_host") or session.get("game_id") != game_id:
        raise HTTPException(status_code=403, detail="호스트만 수행할 수 있습니다.")
    return session


def get_game_status(
    started_at: datetime | None,
    ended_at: datetime | None,
    now: datetime | None = None,
) -> GameStatus:
    current = now or datetime.now(timezone.utc).replace(tzinfo=None)
    if ended_at and current >= ended_at:
        return GameStatus.POSTGAME
    if started_at and current >= started_at:
        return GameStatus.INGAME
    return GameStatus.PREGAME


def get_game_or_404(game_id: int, db: Session) -> Game:
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="게임을 찾을 수 없습니다.")
    return game


def get_leaderboard(
    r: redis.Redis,
    game_id: int,
    db: Session | None = None,
) -> list[LeaderboardEntry]:
    members = r.zrevrangebyscore(
        f"game:{game_id}:leaderboard",
        "+inf",
        "-inf",
        withscores=True,
    )
    result = []

    participants_by_nickname: dict[str, Participant] = {}
    if db is not None and members:
        nicknames = [nickname for nickname, _ in members]
        participants = (
            db.query(Participant)
            .options(selectinload(Participant.guesses))
            .filter(
                Participant.game_id == game_id,
                Participant.nickname.in_(nicknames),
            )
            .all()
        )
        participants_by_nickname = {
            participant.nickname: participant for participant in participants
        }

    for i, (nickname, score) in enumerate(members):
        closest = r.get(f"game:{game_id}:closest:{nickname}")
        participant = participants_by_nickname.get(nickname)

        best_submission = None
        latest_submission = None
        if participant is not None:
            best_guess = get_best_guess(participant)
            latest_guess = get_latest_guess(participant)

            if best_guess is not None:
                best_submission = build_submission_detail(
                    best_guess.word,
                    best_guess.similarity,
                    best_guess.submitted_at,
                )
            elif participant.closest_word is not None:
                best_submission = build_submission_detail(
                    participant.closest_word,
                    participant.best_similarity,
                )

            if latest_guess is not None:
                latest_submission = build_submission_detail(
                    latest_guess.word,
                    latest_guess.similarity,
                    latest_guess.submitted_at,
                )

        result.append(
            LeaderboardEntry(
                rank=i + 1,
                nickname=nickname,
                bestSimilarity=round(score, 4),
                closestWord=closest,
                bestSubmission=best_submission,
                latestSubmission=latest_submission,
            )
        )

    return result
