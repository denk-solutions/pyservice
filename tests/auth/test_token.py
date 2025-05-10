import uuid

import pendulum
import pytest
from pendulum.duration import Duration
from pydantic import HttpUrl, SecretStr, ValidationError

from pyservice.auth.token import Token, sign_access_token, verify_token
from pyservice.context import Settings, temporary_settings
from pyservice.exc import AuthInvalidTokenError


@pytest.fixture
def settings():
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


@pytest.fixture
def user_id():
    return uuid.uuid4(), "test@test.io"


def test_sign_access_token(settings: Settings, user_id):
    sub, email = user_id
    token, expires_in = sign_access_token(sub=sub, email=email)

    assert expires_in == settings.JWT_TOKEN_ACCESS_DURATION.in_seconds()


def test_sign_refresh_token(settings: Settings, user_id):
    sub, email = user_id
    token, expires_in = sign_access_token(sub=sub, email=email)

    assert expires_in == settings.JWT_TOKEN_REFRESH_DURATION.in_seconds()


def test_verify_bad_token(settings):
    with pytest.raises(AuthInvalidTokenError):
        verify_token("bad.jwt.token")


def test_sign_verify_token(settings, user_id):
    sub, email = user_id

    token, expires_in = sign_access_token(sub=sub, email=email)
    claims = verify_token(token)

    assert claims.sub == str(sub)
    assert claims.email == email
    assert (claims.exp - claims.iat) == expires_in


def test_init_token_with_exp_before_iat(user_id):
    sub, email = user_id
    with pytest.raises(ValidationError):
        Token(
            sub=sub,
            email=email,
            iat=pendulum.now("UTC").int_timestamp,
            exp=(pendulum.now("UTC") - Duration(days=1)).int_timestamp,
            aud=[],
            iss=HttpUrl("https://some-issuer"),
        )


def test_init_token_with_insecure_iss(user_id):
    sub, email = user_id
    with pytest.raises(ValidationError):
        Token(
            sub=sub,
            email=email,
            iat=pendulum.now("UTC").int_timestamp,
            exp=(pendulum.now("UTC") + Duration(days=1)).int_timestamp,
            aud=[],
            iss=HttpUrl("http://some-issuer"),
        )
