from datetime import datetime
from typing import Optional

from app.repository.models import GuessHistory, Participant
from app.schemas.game import SubmissionDetail


def build_submission_detail(
    label: Optional[str],
    similarity: Optional[float],
    submitted_at: Optional[datetime] = None,
) -> Optional[SubmissionDetail]:
    if label is None or similarity is None:
        return None
    return SubmissionDetail(
        label=label,
        similarity=round(similarity, 4),
        submittedAt=submitted_at,
    )


def get_latest_guess(participant: Participant) -> Optional[GuessHistory]:
    if not participant.guesses:
        return None
    return max(
        participant.guesses,
        key=lambda guess: (guess.submitted_at, guess.id),
    )


def get_best_guess(participant: Participant) -> Optional[GuessHistory]:
    if not participant.guesses:
        return None

    best_score = round(participant.best_similarity, 4)
    matching_guesses = [
        guess for guess in participant.guesses
        if round(guess.similarity, 4) == best_score
    ]
    if not matching_guesses:
        return None
    if participant.closest_word:
        exact_matches = [
            guess for guess in matching_guesses
            if guess.word == participant.closest_word
        ]
        if exact_matches:
            matching_guesses = exact_matches

    return max(
        matching_guesses,
        key=lambda guess: (guess.submitted_at, guess.id),
    )
