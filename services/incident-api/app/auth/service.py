from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.contracts import PublicUser, RegisterRequest
from app.errors import AppError
from app.interfaces import UserRepository


class JwtAuthService:
    def __init__(self, settings: Settings, users: UserRepository) -> None:
        if settings.jwt_secret is None:
            raise ValueError("JWT_SECRET is required")
        self._settings = settings
        self._users = users
        self._secret = settings.jwt_secret.get_secret_value()
        self._passwords = PasswordHash.recommended()

    @staticmethod
    def _public(user) -> PublicUser:
        return PublicUser(id=user.id, email=user.email, displayName=user.display_name)

    async def register(self, request: RegisterRequest) -> PublicUser:
        if await self._users.get_by_email(str(request.email)) is not None:
            raise AppError.conflict("An account with that email already exists")
        try:
            user = await self._users.create(request, self._passwords.hash(request.password))
        except IntegrityError as error:
            raise AppError.conflict("An account with that email already exists") from error
        return self._public(user)

    async def login(self, email: str, password: str) -> tuple[PublicUser, str]:
        user = await self._users.get_by_email(email)
        if user is None or not self._passwords.verify(password, user.password_hash):
            raise AppError.unauthorized("Invalid email or password")
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": str(user.id),
                "iss": self._settings.jwt_issuer,
                "aud": self._settings.jwt_audience,
                "iat": now,
                "exp": now + timedelta(minutes=self._settings.jwt_expiry_minutes),
            },
            self._secret,
            algorithm=self._settings.jwt_algorithm,
        )
        return self._public(user), token

    async def authenticate(self, token: str | None) -> PublicUser:
        if not token:
            raise AppError.unauthorized()
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._settings.jwt_algorithm],
                issuer=self._settings.jwt_issuer,
                audience=self._settings.jwt_audience,
                options={"require": ["sub", "iss", "aud", "iat", "exp"]},
            )
            user_id = UUID(payload["sub"])
        except (jwt.PyJWTError, ValueError, KeyError) as error:
            raise AppError.unauthorized("Invalid or expired session") from error
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise AppError.unauthorized("Session user no longer exists")
        return self._public(user)
