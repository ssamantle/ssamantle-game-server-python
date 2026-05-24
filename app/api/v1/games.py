from fastapi import APIRouter, Depends, Header, HTTPException
from starlette.requests import Request

from app.schemas.game import (
    CreateGameRequest,
    CreateGameResponse,
    GameInfoResponse,
    GameResultResponse,
    GuessHistoryItem,
    GuessRequest,
    GuessResponse,
    JoinGameRequest,
    JoinGameResponse,
    MessageResponse,
    UpdateEndtimeRequest,
    UpdateWordRequest,
)
from app.service.auth import require_host_session
from app.service.deps import (
    get_game_service,
    get_guess_service,
    get_leaderboard_service,
    get_participant_service,
)
from app.service.exceptions import ServiceException
from app.service.games import GameService, V1_GAME_ID
from app.service.guesses import GuessService
from app.service.leaderboard import LeaderboardService
from app.service.participants import ParticipantService
from http import HTTPStatus
router = APIRouter(prefix="/api/v1/games", tags=["games-v1"])


def raise_http(error: ServiceException) -> None:
    raise HTTPException(status_code=error.status_code, detail=error.detail) from error


@router.post("", response_model=CreateGameResponse, status_code=HTTPStatus.CREATED)
def create_game(
    body: CreateGameRequest,
    request: Request,
    service: GameService = Depends(get_game_service),
):
    try:
        result = service.create_v1_game(body)
    except ServiceException as error:
        raise_http(error)

    request.session.update(result.session.as_session())
    return CreateGameResponse(gameId=result.game_id, sessionId=result.session_id)


@router.post("/join", response_model=JoinGameResponse)
def join_game(
    body: JoinGameRequest,
    request: Request,
    service: ParticipantService = Depends(get_participant_service),
):
    try:
        result = service.join_v1_game(body)
    except ServiceException as error:
        raise_http(error)

    request.session.update(result.session.as_session())
    return JoinGameResponse(
        gameId=result.game_id,
        nickname=result.nickname,
        sessionId=result.session_id,
    )


@router.patch("/time", response_model=MessageResponse)
def update_endtime(
    body: UpdateEndtimeRequest,
    request: Request,
    service: GameService = Depends(get_game_service),
):
    try:
        require_host_session(request.session, V1_GAME_ID)
        service.update_v1_time(body)
    except ServiceException as error:
        raise_http(error)
    return MessageResponse(message="시간이 수정되었습니다.")


@router.patch("/word", response_model=MessageResponse)
def update_word(
    body: UpdateWordRequest,
    request: Request,
    service: GameService = Depends(get_game_service),
):
    try:
        require_host_session(request.session, V1_GAME_ID)
        service.update_v1_word(body)
    except ServiceException as error:
        raise_http(error)
    return MessageResponse(message="단어가 수정되었습니다.")


@router.post("/guess", response_model=GuessResponse)
def guess_word(
    body: GuessRequest,
    authorization: str = Header(...),
    service: GuessService = Depends(get_guess_service),
):
    try:
        return service.submit_v1_guess(body, authorization)
    except ServiceException as error:
        raise_http(error)


@router.get("/polling/db", response_model=GameInfoResponse)
def game_polling_db(
    service: LeaderboardService = Depends(get_leaderboard_service),
):
    try:
        return service.get_v1_game_info_from_db()
    except ServiceException as error:
        raise_http(error)


@router.get("/polling", response_model=GameInfoResponse)
def game_polling(
    service: LeaderboardService = Depends(get_leaderboard_service),
):
    try:
        return service.get_v1_game_info_from_cache()
    except ServiceException as error:
        raise_http(error)


@router.get("/result", response_model=GameResultResponse)
def game_result(service: GameService = Depends(get_game_service)):
    try:
        return service.get_v1_result()
    except ServiceException as error:
        raise_http(error)


@router.post("/end", response_model=MessageResponse)
def end_game(
    request: Request,
    service: GameService = Depends(get_game_service),
):
    try:
        require_host_session(request.session, V1_GAME_ID)
        service.end_v1_game()
    except ServiceException as error:
        raise_http(error)
    return MessageResponse(message="게임이 종료되었습니다.")


@router.get("/guesses", response_model=list[GuessHistoryItem])
def get_guess_history(
    username: str,
    authorization: str = Header(...),
    service: GuessService = Depends(get_guess_service),
):
    try:
        return service.get_v1_guess_history(username, authorization)
    except ServiceException as error:
        raise_http(error)
