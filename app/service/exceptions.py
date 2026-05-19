class ServiceException(Exception):
    status_code = 400
    detail = "잘못된 요청입니다."

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class BadRequestException(ServiceException):
    status_code = 400


class UnauthorizedException(ServiceException):
    status_code = 401
    detail = "인증되지 않은 사용자입니다."


class HostOnlyException(ServiceException):
    status_code = 403
    detail = "호스트만 수행할 수 있습니다."


class GameNotFoundException(ServiceException):
    status_code = 404
    detail = "게임을 찾을 수 없습니다."


class WordNotFoundException(ServiceException):
    status_code = 404


class GameConflictException(ServiceException):
    status_code = 409


class ServiceUnavailableException(ServiceException):
    status_code = 503
