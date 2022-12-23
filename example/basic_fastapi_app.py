from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse

import uvicorn

import AWSLoginHandler.common
from AWSLoginHandler.flows.pkce.manager import PKCEManager

api = FastAPI()

oauth_manager = PKCEManager(
    client_id="17gabj8fffsal3lfb393cv81kc",
    userpool_id="eu-west-2_tMeCEUTj8",
)

oauth_manager.attach_to_app(api)


@api.get("/me", response_class=AWSLoginHandler.common.PrettyJSONResponse)
async def me(
    request: Request, user_info=Depends(oauth_manager.get_user_info_from(["header", "cookie"], auto_error=False))
):
    if user_info:
        return user_info
    else:
        return HTMLResponse(f"Not logged in... click <a href='{request.url_for('login_redirect')}'>here</a> to login")


@api.get("/me/cookie", response_class=AWSLoginHandler.common.PrettyJSONResponse)
async def cookie_me(
    request: Request, user_info=Depends(oauth_manager.get_user_info_from(["cookie"], auto_error=False))
):
    if user_info:
        return user_info
    else:
        return HTMLResponse(f"Not logged in... click <a href='{request.url_for('login_redirect')}'>here</a> to login")


@api.get("/me/header", response_class=AWSLoginHandler.common.PrettyJSONResponse)
async def header_me(request: Request, user_info=Depends(oauth_manager.get_user_info_from(["header"], auto_error=True))):
    if user_info:
        return user_info
    else:
        return f"Not logged in"


uvicorn.run(api, port=8021)
