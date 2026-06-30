"""OAuth2 routes for Google and GitHub social login."""

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.database import get_db
from app.database.repositories.audit import AuditRepository
from app.database.repositories.session import SessionRepository
from app.database.repositories.social_account import SocialAccountRepository
from app.database.repositories.user import UserRepository
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    hash_token,
)
from app.services.cache import cache_service
from app.services.oauth2 import (
    OAUTH2_PROVIDERS,
    exchange_code,
    generate_oauth_state,
    get_authorize_url,
    get_user_info,
)

settings = get_settings()
router = APIRouter(prefix="/api/v1/auth/oauth2", tags=["OAuth2"])


@router.get("/{provider}/login")
async def oauth2_login(provider: str):
    if provider not in OAUTH2_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if not OAUTH2_PROVIDERS[provider]()["client_id"]:
        raise HTTPException(status_code=501, detail=f"{provider} OAuth2 is not configured")

    state = generate_oauth_state()
    await cache_service.set(f"oauth2_state:{state}", provider, ttl=600)

    authorize_url = get_authorize_url(provider, state)
    return RedirectResponse(url=authorize_url, status_code=302)


@router.get("/{provider}/callback")
async def oauth2_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    request: Request = None,
    db=Depends(get_db),
):
    if provider not in OAUTH2_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    frontend_base = settings.oauth2_frontend_redirect_uri

    if error:
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'error': error})}",
            status_code=302,
        )

    if not code:
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'error': 'Authorization code missing'})}",
            status_code=302,
        )

    if not state:
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'error': 'State parameter missing'})}",
            status_code=302,
        )

    stored_provider = await cache_service.get(f"oauth2_state:{state}")
    if not stored_provider or stored_provider != provider:
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'error': 'Invalid or expired state parameter'})}",
            status_code=302,
        )
    await cache_service.delete(f"oauth2_state:{state}")

    try:
        token_data = await exchange_code(provider, code)
    except Exception as exc:
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'error': f'Token exchange failed: {exc}'})}",
            status_code=302,
        )

    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'error': 'Failed to obtain access token'})}",
            status_code=302,
        )

    try:
        user_info = await get_user_info(provider, access_token)
    except Exception as exc:
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'error': f'Failed to fetch user info: {exc}'})}",
            status_code=302,
        )

    provider_user_id = str(user_info.get("id"))
    email = user_info.get("email")
    display_name = user_info.get("name") or user_info.get("login") or email
    avatar_url = user_info.get("picture") or user_info.get("avatar_url")

    if not email:
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'error': 'Email not provided by OAuth provider'})}",
            status_code=302,
        )

    social_repo = SocialAccountRepository(db)
    user_repo = UserRepository(db)

    existing_social = await social_repo.get_by_provider_and_user_id(provider, provider_user_id)

    if existing_social:
        user_id = existing_social["user_id"]
        await social_repo.update_tokens(
            existing_social["id"],
            access_token,
            token_data.get("refresh_token"),
            token_data.get("expires_in"),
        )
    else:
        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            user_id = existing_user["id"]
        else:
            temp_password = secrets.token_urlsafe(32)
            await user_repo.create(email, hash_password(temp_password))
            user_row = await user_repo.get_by_email(email)
            if not user_row:
                return RedirectResponse(
                    url=f"{frontend_base}?error={urlencode({'error': 'Failed to create user'})}",
                    status_code=302,
                )
            user_id = user_row["id"]

        await social_repo.create(
            user_id, provider, provider_user_id, email,
            display_name, avatar_url,
            access_token, token_data.get("refresh_token"),
            token_data.get("expires_in"),
        )

    user_row = await user_repo.get_by_id(user_id)
    if not user_row:
        return RedirectResponse(
            url=f"{frontend_base}?error={urlencode({'error': 'User not found'})}",
            status_code=302,
        )

    jwt_access_token = create_access_token(user_row["email"], role=user_row["role"])
    refresh_token = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)

    sessions = SessionRepository(db)
    await sessions.create(
        user_id, hash_token(refresh_token), expires_at,
        device_name=request.headers.get("user-agent") if request else None,
    )

    if settings.enable_audit_logs:
        audit = AuditRepository(db)
        await audit.create(
            user_id, "oauth2_login",
            resource="auth",
            metadata={"provider": provider, "provider_user_id": provider_user_id},
            ip=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

    params = urlencode({
        "access_token": jwt_access_token,
        "refresh_token": refresh_token,
    })
    return RedirectResponse(url=f"{frontend_base}?{params}", status_code=302)


@router.get("/{provider}/accounts")
async def get_linked_accounts(
    provider: str,
    db=Depends(get_db),
    email: str = Depends(get_current_user),
):
    if provider not in OAUTH2_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    social_repo = SocialAccountRepository(db)
    accounts = await social_repo.get_by_user_id(user["id"])
    return {
        "accounts": [
            {
                "id": a["id"],
                "provider": a["provider"],
                "provider_email": a["provider_email"],
                "display_name": a["display_name"],
                "created_at": str(a["created_at"]),
            }
            for a in accounts
        ]
    }


@router.post("/{provider}/unlink")
async def unlink_social_account(
    provider: str,
    db=Depends(get_db),
    email: str = Depends(get_current_user),
):
    if provider not in OAUTH2_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    social_repo = SocialAccountRepository(db)
    account = await social_repo.get_by_provider_and_email(provider, email)
    if not account:
        raise HTTPException(status_code=404, detail=f"No linked {provider} account found")
    await social_repo.delete(account["id"])
    return {"message": f"{provider} account unlinked"}
