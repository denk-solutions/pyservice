"""
We assume that `pyservice` acts as both a resource server and an authorization server.
The authorization server is isolated from the resource server through a different
primary route of endpoints.

There are two endpoints on the authorization server:
    - POST `/oauth2/token` - used for exchanging an authorization code (or refresh token) for an access token (and another refresh token)
        - must be tls backed.
        - Paramaters:
            client_id
            scope (str): The scope of the requested access. (list of space-delimited, case-sensitive strings)
                         If unspecified, can use default value.
                         Must notify client if different than what was requested.
            authorization_grant:
                - used to get the access token
                - can be four types:
                    authorization-code-grant: best for confidential clients, used to get an access token and refresh token.
                                              - redirection based flow, so client must be able to talk to a browser and receive requests
                                                from the authorization server.

                    implicit-grant: best for public clients, used to get an access token.
                    client-credentials-grant: best for machine-to-machine communication, used to get an access token.
                    password-grant: best for trusted clients, used to get an access token and refresh token.

    - GET `/oauth2/authorize` - used for obtaining an authorization code by the resource owner via a redirect.
         - How the actual resource owner is authenticated in this context is not defined in the spec.
         - Endpoint cannot have a fragment component.
         - may include x-www-form-urlencoded query component.
         - MUST be TLS backed.
         - Valueless parameters are not allowed.
         - No duplicate parameters allowed.

         Parameters:
             response_type (str): The desired grant type, as this endpoint can be used by both the implicit and authorization code flows.
                                  Must be set to 'code', 'token' or a registered extension grant type.

                                  Must return error if response_type is missing or not understood.
             scope (str): The scope of the requested access. (list of space-delimited, case-sensitive strings)

        - Once the resource owner has authenticated, the authorization server redirects them back to the redirect endpoint of the client
          that was registered with the authorization server when the client id was issued.

          NOTE: If there is a redirect_uri parameter, do direct string comparison with registered redirect endpoint and fail flow if they don't match.
          NOTE 2: The client redirection endpoint should not be HTML that executes any third-party javascript as that would have access to the
          credentials the authorization server issued which is a security risk. Instead, it shoud extract the credentials from the URI
          and redirect the user agent to another endpoint.

          The redirection endpoint MUST be an absolute URI as defined by RFC 3986.
          The redirection endpoint may include x-www-form-urlencoded query component and MUST not include fragment.
          If the redirection endpoint is not backed by TLS, warn the resource owner before redirecting.

There is one endpoint on the client:
    - A redirection endpoint used by the authorization server to redirect back to with the authorization grant.


We also assume that `pyservice` has three primary clients:
    - `web` - a confidential, web-based client with their credentials stored in the browser.
    - `mobile-ios` - a public, iOS-based mobile client with their credentials stored on the device.
    - `mobile-android` - a public, Android-based mobile client with their credentials stored on the device.
    - `desktop` - a public desktop client with their credentials stored in the browser.
"""

from typing import Literal

OAUTH2_WEB_CLIENT_ID = ""
OAUTH2_WEB_CLIENT_PASSWORD = ""
"""Web clients are confidential and as such can be authenticated with the authorization server
using HTTP Basic authentication. In this case, TLS is a MUST.
The endpoint must be protected against brute-force attacks, i.e rate limits etc.
"""


OAUTH2_MOBILE_IOS_CLIENT_ID = ""
OAUTH2_MOBILE_ANDROID_CLIENT_ID = ""
OAUTH2_DESKTOP_CLIENT_ID = ""


class Client:
    id: str
    type: Literal["confidential", "public"]
    enabled: bool = False


def main() -> None:
    print("Hello from pyservice!")
