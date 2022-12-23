# AWS Login Handler

A helper module for attaching to a FastAPI app for user login using AWS Cognito.

## Usage
To use add user login to a FastAPI app, simply create a manager and attach it to an app *(The only currently implemented flow is PKCE)*:

```python
from fastapi import FastAPI
from AWSLoginHandler.flows.pkce.manager import PKCEManager

api = FastAPI()

oauth_manager = PKCEManager(
    client_id="7ks1311iid23h0cnvg2o3i4g7k",
    userpool_id="eu-west-2_tMeCEUTj8",
)

oauth_manager.attach_to_app(api)
```

Then to allow a user to login, simply redirect the user to the `/login` endpoint. For example:

```html
<a href='{request.url_for('login_redirect')}'>Login</a>
```

You can get the user information using dependancy injection on your endpoint:

```python
@api.get("/")
async def homepage(request: Request, user_info=Depends(oauth_manager.get_user_info_from(["cookie"], auto_error=False)):
    return user_info
```

You can use the `token_from` parameter in `get_user_info_from` to select where to retrieve the access token. For static websites, you
most likely want to get the access token from the HTTP Only cookie stored after user log-in. For API endpoints, you most
likely want to get the access token from the `Authorization: Bearer {access_token}` header passed to the api endpoint.

An example return value of `get_user_info_from` is:

```json
{
    "user_info": {
        "sub": "b17603a3-00de-44b5-8422-2aea9b70b552", 
        "email_verified": "true", 
        "email": "mcleantom97@gmail.com", 
        "username": "b17603a3-00de-44b5-8422-2aea9b70b552"
    }, 
    "token_payload": {
        "sub": "b17603a3-00de-44b5-8422-2aea9b70b552", 
        "cognito:groups": [
            "bar_technologies"
        ], 
        "iss": "https://cognito-idp.eu-west-2.amazonaws.com/eu-west-2_tMeCEUTj8", 
        "version": 2, 
        "client_id": "17gabj8fffsal3lfb393cv81kc", 
        "origin_jti": "1aa2b8e4-885e-49df-92cf-43197d82fab5", 
        "token_use": "access", 
        "scope": "phone openid email", 
        "auth_time": 1647343413, 
        "exp": 1647347013, 
        "iat": 1647343413, 
        "jti": "02074223-c5f8-46de-8c06-2f74f587d858", 
        "username": "b17603a3-00de-44b5-8422-2aea9b70b552"
    }
}
```

See [the amazon docs](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-access-token.html) for more
information on JWT token payloads.

For a demo, clone the repo to your device. Within the repository, there is a simple FastAPI app in the example folder. 

Create a conda environment, install the dependencies and then run the app

```commandline
conda create -n aws_login_handler
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Run the code and go to

```commandline
http://localhost:8021/
```

The aim of this package is to make it simple to add login handling using AWS Cognito. Before you are able to use the app,
you must first set up an AWS Cognito user pool. Go to [aws cognito](https://eu-west-2.console.aws.amazon.com/cognito/v2/idp/user-pools?region=eu-west-2)
and press 'create user pool'. Set up the pool for your use case.

When you reach `initial app client`, select the correct one for your use case. Public client is used for deployed
apps where you no longer control the source code, confidential client is for server side web apps. Currently, only 
public client is supported. When selecting public client, choose "dont generate a client secret".

For simplicity, select 'Use the Cognito Hosted UI'.

For allowed callback URLs, enter
```commandline
http://localhost:8021/login/redirect
```
Where PORT is the port that you will be running your local test app from (i.e., 8000). After this, keep everything as
default and create your Cognito user pool. It may take some time for the UI to be built.

While your app is being built, go into the example FastAPI app and fill out the details for the PKCEManager for your user pool.
The details can be found by:
* user_pool_id: Go to [here](https://eu-west-2.console.aws.amazon.com/cognito/v2/idp/user-pools?region=eu-west-2) and the pool id is next to the pool name
* client_id: Click on your user pool, go to app integration, go to app client list and the client id is next to the app name
* userpool_id: Scroll to the top of the window, the user pool id is under 'User pool overview'

You can now run `basic_fastapi_app.py` and navigate to `http://localhost:8021/`. Follow the instructions.

### Black and Isort

We use [black](https://github.com/psf/black) to handle code formatting, and [isort](https://pycqa.github.io/isort/) 
for header ordering. 

```commandline
conda create -n aws_login_handler
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

### Todo

* Add `/logout` endpoint
