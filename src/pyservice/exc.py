class PyserviceError(Exception): ...


class AuthError(PyserviceError):
    "Raised when a user authentication error happens."

    ...


class AuthInvalidTokenError(AuthError):
    "Raised when the application tries to sign or verify an invalid token."

    ...


class AuthTokenExpiredError(AuthError):
    "Raised when a verified token has expired."

    ...


class AuthTokenHashVerifyError(AuthError):
    "Raised when a refresh token cannot be verified against its hash."

    ...
