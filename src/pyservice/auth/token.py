import uuid
from enum import Enum
from typing import Any, Protocol, Tuple

import jwt
import pendulum
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

from pyservice.context import SettingsContext
from pyservice.exc import AuthInvalidTokenError
from pyservice.schema import ActionModel, EntityModel


class RefreshTokenStatus(str, Enum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class RefreshToken(EntityModel):
    user_id: uuid.UUID
    status: RefreshTokenStatus
    token_hash: str


class RefreshTokenRotate(ActionModel):
    user_id: uuid.UUID
    token: str | None = None
    user_email: EmailStr | None = None


class RefreshTokenStore(Protocol):
    async def rotate_refresh_token(
        self, user_id: uuid.UUID, token: str | None = None
    ) -> str: ...


class TokenResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str


class Token(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    sub: str = Field(max_length=255)
    email: EmailStr
    iss: HttpUrl
    aud: str | list[str]
    exp: int
    iat: int

    @property
    def expired(self):
        return self.exp < pendulum.now(tz="UTC").int_timestamp

    def intended_for(self, aud: str | list[str]) -> bool:
        if isinstance(self.aud, list):
            return aud in self.aud
        return self.aud == aud

    def get_claim(self, claim: str) -> Any | None:
        return (
            self.__pydantic_extra__.get(claim)
            if self.__pydantic_extra__ is not None
            else None
        )

    @model_validator(mode="after")
    def validate_iat(self):
        if self.iat > self.exp:
            raise ValueError("Invalid token")
        return self

    @field_validator("iss", mode="after")
    @classmethod
    def validate_iss(cls, value):
        if not value.scheme == "https":
            raise ValueError("Invalid token")
        return value


def sign_access_token(*, sub: uuid.UUID, email: EmailStr) -> Tuple[str, int]:
    ctx = SettingsContext.get()

    iat = pendulum.now(tz="UTC")
    exp = iat + ctx.settings.JWT_TOKEN_ACCESS_DURATION

    iss = ctx.settings.JWT_ISSUER_ID
    assert iss is not None

    aud = ctx.settings.JWT_AUDIENCE
    assert aud is not None

    return sign_token(
        Token(
            sub=str(sub),
            email=email,
            iss=iss,
            aud=aud,
            iat=iat.int_timestamp,
            exp=exp.int_timestamp,
        )
    )


def sign_refresh_token(*, sub: uuid.UUID, email: EmailStr) -> Tuple[str, int]:
    ctx = SettingsContext.get()

    iat = pendulum.now(tz="UTC")
    exp = iat + ctx.settings.JWT_TOKEN_REFRESH_DURATION

    iss = ctx.settings.JWT_ISSUER_ID
    assert iss is not None

    aud = ctx.settings.JWT_AUDIENCE
    assert aud is not None

    return sign_token(
        Token(
            sub=str(sub),
            email=email,
            iss=iss,
            aud=aud,
            iat=iat.int_timestamp,
            exp=exp.int_timestamp,
        )
    )


def verify_token(token: str) -> Token:
    ctx = SettingsContext.get()

    key = ctx.settings.JWT_KEY
    assert key is not None

    issuer = ctx.settings.JWT_ISSUER_ID
    assert issuer is not None

    audience = ctx.settings.JWT_AUDIENCE

    try:
        decoded_token: dict[str, Any] = jwt.decode(
            token,
            key.get_secret_value(),
            algorithms=["HS256"],
            issuer=str(issuer),
            audience=audience,
        )
    except jwt.InvalidTokenError as e:
        raise AuthInvalidTokenError("Failed to verify invalid token.") from e

    return Token.model_validate(decoded_token)


def sign_token(token: Token) -> Tuple[str, int]:
    ctx = SettingsContext.get()

    key = ctx.settings.JWT_KEY
    assert key is not None

    payload = token.model_dump(mode="json")
    expires_in = token.exp - token.iat

    try:
        return jwt.encode(
            payload,
            key.get_secret_value(),
            algorithm="HS256",
        ), expires_in
    except jwt.InvalidTokenError as e:
        raise AuthInvalidTokenError("Failed to sign invalid token.") from e
