from functools import cache
from typing import Protocol
from urllib.parse import urlparse

import jwt
from pydantic import HttpUrl

from pyservice.auth.token import (
    RefreshTokenStore,
    Token,
    TokenResult,
    sign_access_token,
)
from pyservice.context import SettingsContext
from pyservice.exc import AuthInvalidTokenError
from pyservice.user import UserCreate, UserStore


class OIDCAuth:
    def __init__(
        self,
        provider: "OIDCProvider",
        user_store: UserStore,
        token_store: RefreshTokenStore,
    ):
        self._provider = provider
        self._user_store = user_store
        self._token_store = token_store

    async def __call__(self, id_token: str) -> TokenResult:
        claims = await self._provider.verify_id_token(id_token)

        create = UserCreate(
            email=claims.email,
            identity_provider=self._provider.name,
            identity_provider_id=claims.sub,
        )
        user_id = await self._user_store.create_user(create, exists_ok=True)

        refresh_token = await self._token_store.rotate_refresh_token(user_id)
        access_token, expires_in = sign_access_token(sub=user_id, email=claims.email)

        return TokenResult(
            access_token=access_token,
            expires_in=expires_in,
            refresh_token=refresh_token,
        )


class OIDCProvider(Protocol):
    async def verify_id_token(self, id_token: str) -> Token: ...

    @property
    def name(self) -> str: ...


class JWKSProvider:
    def __init__(self, uri: HttpUrl, audience: str | list[str]):
        parts = urlparse(str(uri))

        self._client = JWKSProvider.get_client(uri)
        self._issuer = f"{parts.scheme}://{parts.netloc}"
        self._audience = audience

    async def verify_id_token(self, id_token: str) -> Token:
        # TODO: Move to separate loop to not block the main thread.
        try:
            signing_key = self._client.get_signing_key_from_jwt(id_token)

            token_claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=[signing_key.algorithm_name],
                audience=self._audience,
                issuer=self._issuer,
            )
        except (jwt.InvalidTokenError, jwt.PyJWKClientError) as e:
            raise AuthInvalidTokenError(
                f"Could not verify ID token for provider {self.name}"
            ) from e

        result = Token.model_validate(token_claims)
        assert result.intended_for(self._audience)

        return result

    @property
    def name(self) -> str:
        return self._issuer

    @staticmethod
    @cache
    def get_client(uri: HttpUrl):
        return jwt.PyJWKClient(str(uri), cache_jwk_set=True, lifespan=600)


class AppleProvider(JWKSProvider):
    def __init__(self):
        ctx = SettingsContext.get()

        apple_client_id = ctx.settings.OIDC_APPLE_CLIENT_ID
        assert apple_client_id is not None

        super().__init__(
            uri=HttpUrl("https://appleid.apple.com/auth/keys"),
            audience=apple_client_id,
        )

    @property
    def name(self) -> str:
        return "apple"


class GoogleProvider:
    def __init__(self):
        ctx = SettingsContext.get()

        google_client_id = ctx.settings.OIDC_GOOGLE_CLIENT_ID
        assert google_client_id is not None

        self._audience = google_client_id

    async def verify_id_token(self, id_token: str) -> Token:
        import google.auth.transport.requests as grequests
        import google.oauth2.id_token as impl
        from google.auth.exceptions import GoogleAuthError

        session = GoogleProvider._cached_google_session()
        request = grequests.Request(session=session)
        try:
            # TODO: Move to separate loop to not block the main thread.
            #
            # Google verifies the token using public TLS certificates
            # in case their JWKS server doesn't return anything.
            raw_token_claims = impl.verify_oauth2_token(
                id_token=id_token,
                request=request,
                audience=self._audience,
            )
        except GoogleAuthError as e:
            raise AuthInvalidTokenError("Could not verify Google ID token.") from e

        token_claims = Token.model_validate(raw_token_claims)
        assert token_claims.intended_for(self._audience)

        return token_claims

    @property
    def name(self) -> str:
        return "google"

    @staticmethod
    @cache
    def _cached_google_session():
        import requests
        from cachecontrol import CacheControl

        session = requests.Session()
        # Make use of HTTP Cache-Control headers to keep TLS certificates
        # in-memory and avoid roundtrips to certificate authorities.
        return CacheControl(session)
