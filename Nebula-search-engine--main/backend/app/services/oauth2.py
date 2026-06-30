"""OAuth2 authentication service for Google and GitHub."""

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.config import get_settings

settings = get_settings()


def _google_config():
    return {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": "openid email profile",
        "client_id": settings.google_oauth2_client_id,
        "client_secret": settings.google_oauth2_client_secret,
    }


def _github_config():
    return {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "emails_url": "https://api.github.com/user/emails",
        "scopes": "read:user user:email",
        "client_id": settings.github_oauth2_client_id,
        "client_secret": settings.github_oauth2_client_secret,
    }


OAUTH2_PROVIDERS = {
    "google": _google_config,
    "github": _github_config,
}


def get_authorize_url(provider: str, state: str) -> str:
    get_config = OAUTH2_PROVIDERS.get(provider)
    if not get_config:
        raise ValueError(f"Unknown provider: {provider}")

    config = get_config()
    params = {
        "client_id": config["client_id"],
        "redirect_uri": f"{settings.oauth2_redirect_base_uri}/{provider}/callback",
        "response_type": "code",
        "scope": config["scopes"],
        "state": state,
    }
    if provider == "google":
        params["access_type"] = "offline"

    return f"{config['authorize_url']}?{urlencode(params)}"


async def exchange_code(provider: str, code: str) -> dict:
    get_config = OAUTH2_PROVIDERS.get(provider)
    if not get_config:
        raise ValueError(f"Unknown provider: {provider}")

    config = get_config()
    data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "code": code,
        "redirect_uri": f"{settings.oauth2_redirect_base_uri}/{provider}/callback",
        "grant_type": "authorization_code",
    }

    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.post(config["token_url"], data=data, headers=headers)
        response.raise_for_status()
        return response.json()


async def get_user_info(provider: str, access_token: str) -> dict:
    get_config = OAUTH2_PROVIDERS.get(provider)
    if not get_config:
        raise ValueError(f"Unknown provider: {provider}")

    config = get_config()
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.get(config["userinfo_url"], headers=headers)
        response.raise_for_status()
        user_info = response.json()

        if provider == "github":
            primary_email = None
            if not user_info.get("email"):
                emails_resp = await client.get(config["emails_url"], headers=headers)
                emails_resp.raise_for_status()
                emails = emails_resp.json()
                primary_email = next(
                    (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                    None,
                )
            user_info["email"] = user_info.get("email") or primary_email

        return user_info


def generate_oauth_state() -> str:
    return secrets.token_urlsafe(32)
