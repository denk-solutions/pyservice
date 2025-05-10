import uuid

from fastapi import APIRouter, HTTPException, status

from pyservice.api.dependencies import (
    BearerToken,
    RefreshTokenStoreImpl,
    UserStoreImpl,
)
from pyservice.auth.oidc import AppleProvider, GoogleProvider, OIDCAuth
from pyservice.auth.token import TokenResult, sign_access_token, verify_token

router = APIRouter(prefix="/auth")


@router.post("/google", response_model=TokenResult)
async def google(
    credentials: BearerToken,
    user_store: UserStoreImpl,
    refresh_token_store: RefreshTokenStoreImpl,
):
    authenticate = OIDCAuth(GoogleProvider(), user_store, refresh_token_store)
    response = await authenticate(credentials.credentials)
    return response


@router.post("/apple", response_model=TokenResult)
async def apple(
    credentials: BearerToken,
    user_store: UserStoreImpl,
    refresh_token_store: RefreshTokenStoreImpl,
):
    authenticate = OIDCAuth(AppleProvider(), user_store, refresh_token_store)
    result = await authenticate(credentials.credentials)
    return result


@router.post("/refresh", response_model=TokenResult)
async def refresh(credentials: BearerToken, refresh_token_store: RefreshTokenStoreImpl):
    token = verify_token(credentials.credentials)
    if token.expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user_id = uuid.UUID(token.sub)

    refresh_token = await refresh_token_store.rotate_refresh_token(
        user_id, token=credentials.credentials
    )
    access_token, expires_in = sign_access_token(sub=user_id, email=token.email)

    return TokenResult(
        access_token=access_token,
        expires_in=expires_in,
        refresh_token=refresh_token,
    )
