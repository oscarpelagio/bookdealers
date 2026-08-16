"""Jerarquia d'errors del domini d'autenticació.

Cada error duu associat un `status_code` HTTP i un `code` estable
perquè els clients puguin reaccionar de forma programàtica sense
dependre de missatges (que poden canviar).
"""

from fastapi import status


class AuthError(Exception):
    """Error base de tots els errors del domini d'autenticació."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "auth_error"
    message: str = "Authentication error."

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        self.message = message or self.message
        if code is not None:
            self.code = code
        super().__init__(self.message)

    def to_payload(self) -> dict:
        return {"error": self.code, "message": self.message}


class AuthenticationError(AuthError):
    """Fallida d'autenticació genèrica (401)."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class InvalidCredentialsError(AuthenticationError):
    """Credencials incorrectes. Missatge genèric: no revela si l'email existeix."""

    code = "invalid_credentials"
    message = "Invalid email or password."


class TokenMissingError(AuthenticationError):
    code = "token_missing"
    message = "Authentication required."


class TokenInvalidError(AuthenticationError):
    code = "token_invalid"
    message = "Invalid token."


class TokenExpiredError(AuthenticationError):
    code = "token_expired"
    message = "Token has expired."


class TokenRevokedError(AuthenticationError):
    code = "token_revoked"
    message = "Token has been revoked."


class UserDisabledError(AuthenticationError):
    code = "user_disabled"
    message = "User account is disabled."


class ForbiddenError(AuthError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "You do not have permission to perform this action."


class TooManyAttemptsError(AuthError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "too_many_attempts"
    message = "Too many attempts. Try again later."


class WeakPasswordError(AuthError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "weak_password"
    message = "Password does not meet security requirements."


class UserAlreadyExistsError(AuthError):
    status_code = status.HTTP_409_CONFLICT
    code = "already_exists"
    message = "Resource already exists."


class TokenNotFoundError(AuthError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "token_not_found"
    message = "Token is invalid or has expired."


class EmailVerificationError(AuthError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "email_not_verified"
    message = "Email verification failed."


class GoogleAuthError(AuthenticationError):
    code = "google_auth_failed"
    message = "Google authentication failed."


class GoogleTokenInvalidError(GoogleAuthError):
    code = "google_token_invalid"
    message = "Invalid Google credential."
