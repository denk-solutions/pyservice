import pytest
import pytest_asyncio
from pendulum import Duration
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from pyservice.auth.token import RefreshTokenStatus
from pyservice.context import Settings, temporary_settings
from pyservice.exc import AuthTokenHashVerifyError
from pyservice.pg.context import DatabaseContext, get_database_url
from pyservice.pg.models import PGRefreshToken
from pyservice.pg.store import Store
from pyservice.user import UserCreate

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest_asyncio.fixture
async def store():
    from pyservice.pg.models import Base

    database_url = get_database_url()
    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    with DatabaseContext(engine=engine) as ctx:
        async with ctx.session() as session:
            async with session.begin():
                yield Store(session)
        async with ctx.session() as session:
            async with session.begin():
                for table in Base.metadata.sorted_tables:
                    await session.execute(table.delete())


@pytest_asyncio.fixture
async def user_in_db(store: Store):
    create = UserCreate(
        email="test@test.io",
        identity_provider="apple",
        identity_provider_id="1",
    )
    user_id = await store.create_user(create)
    return user_id


@pytest.fixture
def jwt_settings():
    with temporary_settings(
        updates={
            "JWT_KEY": SecretStr("test-key"),
            "JWT_ISSUER_ID": "https://pyservice-test/",
            "JWT_AUDIENCE": ["ios", "android"],
            "JWT_TOKEN_ACCESS_DURATION": Duration(hours=1),
            "JWT_TOKEN_REFRESH_DURATION": Duration(hours=1),
        }
    ) as ctx:
        yield ctx.settings


async def test_create_user_same_user(store: Store):
    create = UserCreate(
        email="test@test.io",
        identity_provider="apple",
        identity_provider_id="1",
    )

    uuid_one = await store.create_user(create)
    uuid_two = await store.create_user(create, exists_ok=True)

    assert uuid_one == uuid_two

    with pytest.raises(IntegrityError):
        _ = await store.create_user(create)


async def test_create_user_for_different_providers(store: Store):
    create_one = UserCreate(
        email="test@test.io",
        identity_provider="apple",
        identity_provider_id="1",
    )

    _ = await store.create_user(create_one)

    create_two = UserCreate(
        email="test@test.io",
        identity_provider="google",
        identity_provider_id="2",
    )
    with pytest.raises(IntegrityError):
        _ = await store.create_user(create_two, exists_ok=True)


async def test_rotate_refresh_token_only_one_active(
    store: Store, jwt_settings: Settings, user_in_db
):
    for _ in range(5):
        _ = await store.rotate_refresh_token(user_in_db)

    result = await store._session.execute(
        select(PGRefreshToken.status).where(PGRefreshToken.user_id == user_in_db)
    )
    result = [row[0] for row in result.fetchall()]

    assert (
        len(list(filter(lambda status: status == RefreshTokenStatus.ACTIVE, result)))
        == 1
    )
    assert (
        len(list(filter(lambda status: status == RefreshTokenStatus.REVOKED, result)))
        == 4
    )


async def test_rotate_refresh_token_verification(
    store: Store, jwt_settings: Settings, user_in_db
):
    token_one = await store.rotate_refresh_token(user_in_db)
    token_two = await store.rotate_refresh_token(user_in_db, token=token_one)

    assert token_one != token_two

    with pytest.raises(AuthTokenHashVerifyError):
        _ = await store.rotate_refresh_token(user_in_db, token="invalid token")
