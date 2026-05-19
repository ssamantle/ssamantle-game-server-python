from fastapi import APIRouter, Depends, Header

from app.service.auth import AuthService
from app.service.deps import get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/validate")
def validate_token(
    authorization: str = Header(...),
    service: AuthService = Depends(get_auth_service),
):
    """세션ID(토큰) 유효성 검사"""
    return service.validate_token(authorization)
