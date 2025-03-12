from fastapi import HTTPException, status


class NotFoundError(HTTPException):  # type: ignore
    def __init__(self, detail: str = 'Not Found'):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestError(HTTPException):  # type: ignore
    def __init__(self, detail: str = 'Bad Request'):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail
        )


class InternalServerError(HTTPException):  # type: ignore
    def __init__(self, detail: str = 'Internal Server Error'):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )
