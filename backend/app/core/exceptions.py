"""Error base de dominio de los módulos sociales.

Mismo patrón que `app.auth.exceptions.AuthError`: cada error lleva un
`status_code` HTTP y un `code` estable para que los clientes puedan
reaccionar de forma programática sin depender de los mensajes.
"""

from fastapi import status


class DomainError(Exception):
    """Error base de todos los errores de dominio sociales."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "domain_error"
    message: str = "Domain error."

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        self.message = message or self.message
        if code is not None:
            self.code = code
        super().__init__(self.message)

    def to_payload(self) -> dict:
        return {"error": self.code, "message": self.message}
