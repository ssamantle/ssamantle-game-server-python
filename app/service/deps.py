from fastapi import Depends
from sqlalchemy.orm import Session

from app.repository.database import get_db
from app.repository.deps import (
    get_game_cache_repository,
    get_game_repository,
    get_guess_history_repository,
    get_leaderboard_repository,
    get_participant_cache_repository,
    get_participant_repository,
    get_vector_store,
)
from app.repository.rdb import GameRepository, GuessHistoryRepository
from app.repository.rdb import ParticipantRepository
from app.repository.redis import GameCacheRepository, LeaderboardRepository, ParticipantCacheRepository
from app.repository.vector import VectorStore
from app.service.auth import AuthService
from app.service.games import GameService
from app.service.guesses import GuessService
from app.service.leaderboard import LeaderboardService
from app.service.participants import ParticipantService


def get_auth_service(
    games: GameRepository = Depends(get_game_repository),
    participants: ParticipantRepository = Depends(get_participant_repository),
) -> AuthService:
    return AuthService(games=games, participants=participants)


def get_game_service(
    db: Session = Depends(get_db),
    games: GameRepository = Depends(get_game_repository),
    participants: ParticipantRepository = Depends(get_participant_repository),
    leaderboard: LeaderboardRepository = Depends(get_leaderboard_repository),
    participant_cache: ParticipantCacheRepository = Depends(get_participant_cache_repository),
    game_cache: GameCacheRepository = Depends(get_game_cache_repository),
    vector_store: VectorStore = Depends(get_vector_store),
) -> GameService:
    return GameService(
        db=db,
        games=games,
        participants=participants,
        leaderboard=leaderboard,
        participant_cache=participant_cache,
        game_cache=game_cache,
        vector_store=vector_store,
    )


def get_participant_service(
    db: Session = Depends(get_db),
    games: GameRepository = Depends(get_game_repository),
    participants: ParticipantRepository = Depends(get_participant_repository),
    leaderboard: LeaderboardRepository = Depends(get_leaderboard_repository),
    participant_cache: ParticipantCacheRepository = Depends(
        get_participant_cache_repository
    ),
) -> ParticipantService:
    return ParticipantService(
        db=db,
        games=games,
        participants=participants,
        leaderboard=leaderboard,
        participant_cache=participant_cache,
    )


def get_guess_service(
    db: Session = Depends(get_db),
    games: GameRepository = Depends(get_game_repository),
    participants: ParticipantRepository = Depends(get_participant_repository),
    participant_cache: ParticipantCacheRepository = Depends(get_participant_cache_repository),
    guesses: GuessHistoryRepository = Depends(get_guess_history_repository),
    leaderboard: LeaderboardRepository = Depends(get_leaderboard_repository),
    vector_store: VectorStore = Depends(get_vector_store),
) -> GuessService:
    return GuessService(
        db=db,
        games=games,
        participants=participants,
        participant_cache=participant_cache,
        guesses=guesses,
        leaderboard=leaderboard,
        vector_store=vector_store,
    )


def get_leaderboard_service(
    games: GameRepository = Depends(get_game_repository),
    participants: ParticipantRepository = Depends(get_participant_repository),
    participant_cache: ParticipantCacheRepository = Depends(get_participant_cache_repository),
    leaderboard: LeaderboardRepository = Depends(get_leaderboard_repository),
    game_cache: GameCacheRepository = Depends(get_game_cache_repository),
) -> LeaderboardService:
    return LeaderboardService(
        games=games,
        participants=participants,
        participant_cache=participant_cache,
        leaderboard=leaderboard,
        game_cache=game_cache,
    )
