from __future__ import annotations

from app.repository.models import Game

# 현재 진행 중인 게임 객체를 메모리에 캐싱 (DB 조회 없이 game 정보 접근용)

# TODO: V1에서는 백엔드 서버가 하나이고, 진행 중인 게임의 수도 하나로 고정되기 때문에 가능한 로직입니다.
# V2로 버전이 넘어갈 경우 RestAPI에서 pathVarible로 게임 ID를 가져오고, Redis에 게임 정보를 기록하는 구조로 변경하는 것이 좋을 것 같습니다.
_current_game: Game | None = None


def get_current_game() -> Game | None:
    return _current_game


def set_current_game(game: Game) -> None:
    # 게임 생성/수정/종료 시 호출해 전역 상태를 최신으로 유지
    global _current_game
    _current_game = game
