import secrets
from typing import Dict, Optional

import aiohttp
import requests
from fastapi import APIRouter, Cookie, FastAPI, Request, status
from fastapi.exceptions import HTTPException
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from AWSLoginHandler.common import PrettyJSONResponse, generate_query_params, generate_state
from AWSLoginHandler.flows.base import OAuthManager
from AWSLoginHandler.flows.pkce.verifier_challenge import generate_pkce_pair

__all__ = ["PKCEManager"]


class PKCEAuthorizationRequest(BaseModel):
    response_type: str = "code"
    client_id: str
    redirect_uri: str
    state: str
    scope: str
    code_challenge: str
    code_challenge_method: str = "S256"


class PKCETokenRequest(BaseModel):
    grant_type: str = "authorization_code"
    client_id: str
    redirect_uri: str
    code: str
    code_verifier: str


class CodeResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class PKCEManager(OAuthManager):
    def __init__(
        self,
        client_id: str,
        userpool_id: str,
        login_prefix: str = "/login",
        scopes: Optional[Dict[str, str]] = None,
    ):
        self.user_pool_id = userpool_id
        self.client_secret = client_secret
        self.region = self.user_pool_id.split("_")[0]
        self.openid_keys = requests.get(
            f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/openid-configuration"
        ).json()
        self.authorization_url = self.openid_keys["authorization_endpoint"]
        self.token_url = self.openid_keys["token_endpoint"]
        self.refresh_url = self.openid_keys["token_endpoint"]
        self.user_info_url = self.openid_keys["userinfo_endpoint"]
        self.client_id = client_id
        self.login_prefix = login_prefix
        self.keys_url = self.openid_keys["jwks_uri"]
        self.keys = requests.get(self.keys_url).json()["keys"]

        if not scopes:
            scopes = {}

        self.scopes = scopes

        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            authorizationCode={
                "authorizationUrl": self.authorization_url,
                "tokenUrl": self.token_url,
                "refreshUrl": self.refresh_url,
                "scopes": self.scopes,
            }
        )

        super().__init__(flows=flows)

    def attach_to_app(self, app: FastAPI):
        app.swagger_ui_init_oauth = {"usePkceWithAuthorizationCodeGrant": True}
        app.setup()

        router = APIRouter(prefix=self.login_prefix)

        @router.get("/")
        async def login_redirect(request: Request):
            state = generate_state()
            code_verifier, code_challenge = generate_pkce_pair()
            redirect_uri = f"{request.base_url}{self.login_prefix.lstrip('/')}/redirect"
            pkce_authorization_request = PKCEAuthorizationRequest(
                client_id=self.client_id,
                redirect_uri=redirect_uri,
                scope="email+openid+phone",
                state=state,
                code_challenge=code_challenge,
                code_challenge_method="S256",
            )

            query_params = generate_query_params(**pkce_authorization_request.dict())
            authorization_redirect_uri = f"{self.authorization_url}?{query_params}"

            response = RedirectResponse(authorization_redirect_uri, status_code=status.HTTP_307_TEMPORARY_REDIRECT,)

            response.set_cookie(
                key="post_redirect_uri", value=request.headers.get("referer"), httponly=True,
            )
            response.set_cookie(key="code_challenge", value=code_challenge, httponly=True)
            response.set_cookie(key="code_verifier", value=code_verifier, httponly=True)
            response.set_cookie(key="redirect_uri", value=redirect_uri, httponly=True)
            response.set_cookie(key="state", value=state, httponly=True)
            return response

        @router.get("/redirect")
        async def redirect(request: Request, post_redirect_uri: str = Cookie(None)):

            returned_state = request.query_params["state"]
            previous_state = request.cookies.get("state")
            if not secrets.compare_digest(previous_state, returned_state):
                raise HTTPException(detail="Invalid request", status_code=status.HTTP_401_UNAUTHORIZED)

            token_data = PKCETokenRequest(
                client_id=self.client_id,
                redirect_uri=request.cookies.get("redirect_uri"),
                code=request.query_params["code"],
                code_verifier=request.cookies.get("code_verifier"),
            )

            form_data = aiohttp.FormData(fields=token_data.dict())
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=form_data, headers=headers) as server_response:
                    token_response = await server_response.json()

            if server_response.status == status.HTTP_200_OK:
                token_response = CodeResponse(**token_response)
                response = RedirectResponse(post_redirect_uri)

                response.set_cookie(
                    key="access_token",
                    value=token_response.access_token,
                    expires=token_response.expires_in,
                    httponly=True,
                )
                response.set_cookie(
                    key="refresh_token", value=token_response.refresh_token, httponly=True,
                )
                response.delete_cookie("post_redirect_uri")
                response.delete_cookie("state")
                response.delete_cookie("redirect_uri")
                response.delete_cookie("code_verifier")
                response.delete_cookie("code_challenge")
                return response
            else:
                raise HTTPException(detail=token_response, status_code=server_response.status)

        @router.get("/token/refresh")
        async def refresh_access_token(request: Request):
            """
            The refresh endpoint should go to the cognito endpoint and exchange the refresh_token cookie for a new
            access token. If the refresh token is invalid, or for some reason cannot get a new access token, it
            should redirect to the /logout endpoint.

            The 'get_user' and 'get_user_info' should redirect to here to try and refresh the access token if they
            are not able to get the user info for some reason (token invalid). They should use
            'request.get_url_for('/token/refresh')' to get the url to go to and use a tem

            The refresh token endpoint should use a query parameter to redirect back to the page, or use
            'request.headers.get("referer")' to get the page location from the 'get_user' and 'get_user_info'
            functions.
            """
            raise HTTPException(
                detail="Not currently implemented", status_code=status.HTTP_501_NOT_IMPLEMENTED,
            )

        @router.get("/token/introspect", response_class=PrettyJSONResponse)
        async def token_introspection(request: Request) -> Dict[str, Dict[str, str]]:
            user_info = await self.get_user_info(request)
            token_info = await self.get_users_token_payload(request)
            return {"user_info": user_info, "token_info": token_info}

        @router.get("/logout")
        async def logout(request: Request):
            """
            The logout endpoint should go to the aws cognito /logout endpoint as well as
            """
            raise HTTPException(
                detail="Not currently implemented", status_code=status.HTTP_501_NOT_IMPLEMENTED,
            )

        app.include_router(router)
