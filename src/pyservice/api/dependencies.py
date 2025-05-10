from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from pyservice.auth.token import RefreshTokenStore
from pyservice.pg.context import DatabaseContext
from pyservice.pg.store import Store
from pyservice.user import UserStore


async def get_database_tx():
    ctx = DatabaseContext.get()
    async with ctx.session() as session:
        async with session.begin():
            yield session


DatabaseTx = Annotated[AsyncSession, Depends(get_database_tx)]


async def get_database_store(tx: DatabaseTx):
    return Store(tx)


RefreshTokenStoreImpl = Annotated[RefreshTokenStore, Depends(get_database_store)]
UserStoreImpl = Annotated[UserStore, Depends(get_database_store)]

BearerToken = Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]
