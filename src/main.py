from functools import lru_cache
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from starlette.responses import RedirectResponse
import random
import re
import src.config as config
import uuid
import json
from slack_bolt.oauth.async_oauth_flow import AsyncOAuthFlow
from slack_bolt.oauth.async_oauth_settings import AsyncOAuthSettings
from slack_sdk.oauth.installation_store.sqlite3 import SQLite3InstallationStore
from slack_sdk.oauth.state_store.sqlite3 import SQLite3OAuthStateStore
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from src.util.constants import success_responses, error_responses
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

import logging

logging.basicConfig(level=logging.DEBUG)

app = FastAPI()


@lru_cache()
def get_settings():
    return config.Settings()


oauth_flow = AsyncOAuthFlow.sqlite3(
    client_id=get_settings().slack_client_id,
    client_secret=get_settings().slack_client_secret,
    scopes=get_settings().slack_scopes.split(','),
    database='./slackapp.db',
)
slack_app = AsyncApp(
    token=get_settings().slack_bot_token,
    signing_secret=get_settings().slack_signing_secret,
    oauth_flow=oauth_flow,
)
app_handler = AsyncSlackRequestHandler(slack_app)


@slack_app.event("app_mention")
async def handle_app_mentions(body, say, logger):
    logger.info(body)
    await say("What's up?")


@slack_app.event("message")
async def handle_message():
    pass


@slack_app.command("/kudos")
async def command(ack, body, client):
    if body.get('text', None) == "help":
        await ack(f'To use Kudosbot, just type in /kudos and press enter in any chat.');
        return
    else:
        await ack()
        with open('/app/src/modal/kudos.json') as f:
            data = json.load(f)
        await client.views_open(trigger_id=body['trigger_id'], view=data)


@slack_app.view('kudos_modal')
async def handle_kudos_submission(ack, body, client, logger):
    data = body
    logger.debug(f"Data: {data}")
    values = data['view']['state']['values']
    channel_id = values['channel']['id']['selected_channel']
    message = values['custom']['message']['value']
    users = ["<@" + user + ">" for user in values['receivers']['id']["selected_users"]]
    sender = data['user']

    await ack()
    new_payload = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Hello, " + " ".join(users) + "! You've gotten a kudos :cherry_blossom:"
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*<@" + sender['id'] + ">*\n" + message + ""
            },
        },
        {
            "type": "image",
            "image_url": "https://media.giphy.com/media/3oz8xEw5k7ae09nFFm/giphy.gif",
            "alt_text": "yayy"
        }
    ]
    try:
        await client.chat_postMessage(blocks=new_payload, channel=channel_id)
        payload = "Hello Kudo-er! Your kudos has been delivered. " + success_responses[
            random.randint(0, len(success_responses) - 1)]
    except Exception as e:
        payload = error_responses[random.randint(0, len(error_responses) - 1)]
    finally:
        await client.chat_postMessage(text=payload, channel=sender['id'])
    return


@app.post("/slack/events")
async def endpoint(req: Request):
    return await app_handler.handle(req)


@app.get("/slack/install")
async def install(req: Request):
    # return await app_handler.handle(req)
    state = await slack_app.oauth_flow.issue_new_state(request=req)
    url = await slack_app.oauth_flow.build_authorize_url(state=state, request=req)
    res = RedirectResponse(url=url, status_code=302)
    res.set_cookie('slack-app-oauth-state', state)
    return res


@app.get("/slack/oauth_redirect")
async def oauth_redirect(req: Request):
    return await app_handler.handle(req)
