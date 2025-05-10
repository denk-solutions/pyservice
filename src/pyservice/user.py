import uuid
from typing import Protocol

from pydantic import EmailStr

from pyservice.schema import ActionModel, EntityModel


class User(EntityModel):
    email: EmailStr
    identity_provider: str
    identity_provider_id: str


class UserCreate(ActionModel):
    email: EmailStr
    identity_provider: str
    identity_provider_id: str


class UserStore(Protocol):
    async def create_user(
        self, create: UserCreate, *, exists_ok: bool = False
    ) -> uuid.UUID: ...
