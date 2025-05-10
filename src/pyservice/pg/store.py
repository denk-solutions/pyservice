import uuid

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from pyservice.auth.context import HashContext
from pyservice.auth.token import (
    RefreshTokenStatus,
    sign_refresh_token,
)
from pyservice.exc import AuthTokenHashVerifyError
from pyservice.pg.models import PGRefreshToken, PGUser
from pyservice.pg.utils import UserIdentity
from pyservice.user import UserCreate


class Store:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_user(
        self, create: UserCreate, *, exists_ok: bool = False
    ) -> uuid.UUID:
        stmt = insert(PGUser).values(
            email=create.email,
            identity=UserIdentity(
                provider=create.identity_provider, id=create.identity_provider_id
            ),
        )
        if exists_ok:
            stmt = stmt.on_conflict_do_update(
                index_elements=[PGUser.identity], set_={"email": PGUser.email}
            )
        stmt = stmt.returning(PGUser.id)

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def read_user_email(self, user_id: uuid.UUID) -> str | None:
        stmt = select(PGUser.email).where(PGUser.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def rotate_refresh_token(
        self, user_id: uuid.UUID, token: str | None = None
    ) -> str:
        stmt = (
            select(PGRefreshToken.id, PGRefreshToken.token_hash)
            .where(
                (PGRefreshToken.status == RefreshTokenStatus.ACTIVE)
                & (PGRefreshToken.user_id == user_id)
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row:
            pg_token_id, pg_token_hash = row._t

            ctx = HashContext.get()
            if token and not ctx.crypt.verify(token, pg_token_hash):
                raise AuthTokenHashVerifyError("Refresh token hash mismatch.")

            stmt = (
                update(PGRefreshToken)
                .where(PGRefreshToken.id == pg_token_id)
                .values(status=RefreshTokenStatus.REVOKED)
            )
            _ = await self._session.execute(stmt)

        user_email = await self.read_user_email(user_id)
        assert user_email is not None

        refresh_token, _ = sign_refresh_token(sub=user_id, email=user_email)

        stmt = insert(PGRefreshToken).values(
            token_hash=refresh_token,
            user_id=user_id,
            status=RefreshTokenStatus.ACTIVE,
        )
        _ = await self._session.execute(stmt)

        return refresh_token
