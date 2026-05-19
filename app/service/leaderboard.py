from __future__ import annotations

from datetime import datetime, timezone

from app.repository.rdb import GameRepository, ParticipantRepository
from app.repository.redis import LeaderboardRepository
from app.schemas.game import GameInfoResponse, SubmissionSummary, UserInfo
from app.service.exceptions import GameNotFoundException
from app.service.games import V1_GAME_ID
from app.utils import get_best_guess, get_latest_guess


def to_unix_ms(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


class LeaderboardService:
    def __init__(
        self,
        games: GameRepository,
        participants: ParticipantRepository,
        leaderboard: LeaderboardRepository,
    ):
        self.games = games
        self.participants = participants
        self.leaderboard = leaderboard

    def get_v1_game_info_from_cache(self) -> GameInfoResponse:
        game = self.games.find_by_id(V1_GAME_ID)
        if game is None:
            raise GameNotFoundException()

        entries = self.leaderboard.list_entries(V1_GAME_ID)
        participant_ids = [participant_id for participant_id, _ in entries]
        participants = self.participants.list_by_game_and_ids_with_guesses(
            V1_GAME_ID,
            participant_ids,
        )
        participants_by_id = {
            participant.id: participant for participant in participants
        }

        users = []
        for rank, (participant_id, score) in enumerate(entries, start=1):
            participant = participants_by_id.get(participant_id)
            if participant is None:
                continue
            users.append(
                UserInfo(
                    name=participant.nickname,
                    bestSimilarity=round(score, 4),
                    rank=rank,
                    bestSubmission=_build_submission_summary(get_best_guess(participant)),
                    latestSubmission=_build_submission_summary(
                        get_latest_guess(participant)
                    ),
                )
            )

        return GameInfoResponse(
            startAt=to_unix_ms(game.started_at),
            endAt=to_unix_ms(game.ended_at),
            users=users,
        )

    def get_v1_game_info_from_db(self) -> GameInfoResponse:
        game = self.games.find_by_id(V1_GAME_ID)
        if game is None:
            raise GameNotFoundException()

        participants = (
            self.participants.list_by_game_with_guesses_ordered_by_best_similarity(
                V1_GAME_ID
            )
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
