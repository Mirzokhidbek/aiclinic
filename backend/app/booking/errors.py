class BookingError(Exception):
    """Domain error with a stable code; the API layer maps it to an HTTP response."""

    status = 400

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NotFoundError(BookingError):
    status = 404


class ConflictError(BookingError):
    status = 409


class GoneError(BookingError):
    status = 410
