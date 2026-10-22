from typing import Annotated
from uuid import UUID

from pydantic import EmailStr, Field

from app.contracts.api import ApiModel


class AuthRequest(ApiModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=12, max_length=128)]


class RegisterRequest(AuthRequest):
    display_name: Annotated[str, Field(alias="displayName", min_length=1, max_length=120)]


class PublicUser(ApiModel):
    id: UUID
    email: EmailStr
    display_name: str = Field(alias="displayName")
