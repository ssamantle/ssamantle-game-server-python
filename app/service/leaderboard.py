from __future__ import annotations

from datetime import datetime, timezone

from app.core.logger import getLogger
from app.repository.rdb import GameRepository, ParticipantRepository
from app.repository.redis import LeaderboardRepository, ParticipantCacheRepository
from app.schemas.game import GameInfoResponse, SubmissionSummary, UserInfo
from app.service.exceptions import GameNotFoundException
from app.service.game_state import get_current_game
from app.service.games import V1_GAME_ID
from app.utils import get_best_guess, get_latest_guess

logger = getLogger(__name__)


def to_unix_ms(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


class LeaderboardService:
    def __init__(
        self,
        games: GameRepository,
        participants: ParticipantRepository,
        participant_cache: ParticipantCacheRepository,
        leaderboard: LeaderboardRepository,
    ):
        self.games = games
        self.participants = participants
        self.participant_cache = participant_cache
        self.leaderboard = leaderboard

    def get_v1_game_info_from_cache(self) -> GameInfoResponse:
        logger.debug(
            "Polling request received - source=cache gameId=%d",
            V1_GAME_ID,
        )
        game = get_current_game()
        if game is None:
            logger.warning(
                "Polling cache aborted - game not found in RDB gameId=%d",
                V1_GAME_ID,
            )
            raise GameNotFoundException()

        entries = self.leaderboard.list_entries(V1_GAME_ID)
        if entries:
            logger.debug(
                "Polling cache hit - gameId=%d leaderboardEntries=%d",
                V1_GAME_ID,
                len(entries),
            )
        else:
            logger.info(
                "Polling cache miss - gameId=%d leaderboardEntries=0",
                V1_GAME_ID,
            )
        participants = self.participant_cache.get_all(V1_GAME_ID)

        users = []
        for rank, (participant_id, score) in enumerate(entries, start=1):
            participant = participants.get(participant_id)
            if participant is None:
                continue
            users.append(
                UserInfo(
                    name=participant["nickname"],
                    bestSimilarity=round(score, 4),
                    rank=rank,
                    bestSubmission=SubmissionSummary(
                        similarity=participant["bestSimilarity"],
                        wordRank=participant["bestWordRank"],
                    ) if participant["bestSimilarity"] > 0 else None,
                    latestSubmission=SubmissionSummary(
                        similarity=participant["latestSimilarity"],
                        wordRank=participant["latestWordRank"],
                    ) if participant["latestSimilarity"] > 0 else None,
                )
            )

        logger.debug(
            "Polling cache response built - gameId=%d users=%d",
            V1_GAME_ID,
            len(users),
        )
        return GameInfoResponse(
            startAt=to_unix_ms(game.started_at),
            endAt=to_unix_ms(game.ended_at),
            users=users,
        )

    def get_v1_game_info_from_db(self) -> GameInfoResponse:
        logger.debug(
            "Polling request received - source=db gameId=%d",
            V1_GAME_ID,
        )
        game = self.games.find_by_id(V1_GAME_ID)
        if game is None:
            logger.warning(
                "Polling DB aborted - game not found in RDB gameId=%d",
                V1_GAME_ID,
            )
            raise GameNotFoundException()

        participants = (
            self.participants.list_by_game_with_guesses_ordered_by_best_similarity(
                V1_GAME_ID
            )
        )
        logger.debug(
            "Polling DB query completed - gameId=%d participants=%d",
            V1_GAME_ID,
            len(participants),
        )
        users = [
            UserInfo(
                name=participant.nickname,
                bestSimilarity=round(participant.best_similarity, 4),
                rank=i + 1,
                bestSubmission=_build_submission_summary(get_best_guess(participant)),
                latestSubmission=_build_submission_summary(get_latest_guess(participant)),
            )
            for i, participant in enumerate(participants)
        ]
        logger.debug(
            "Polling DB response built - gameId=%d users=%d",
            V1_GAME_ID,
            len(users),
        )
        return GameInfoResponse(
            startAt=to_unix_ms(game.started_at),
            endAt=to_unix_ms(game.ended_at),
            users=users,
        )


def _build_submission_summary(guess) -> SubmissionSummary | None:
    if guess is None:
        return None
    return SubmissionSummary(
        similarity=round(guess.similarity, 4),
        wordRank=guess.word_rank,
    )
