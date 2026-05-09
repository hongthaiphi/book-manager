"""
Google OAuth 2.0 flow:
  1. GET /api/auth/google           → redirect to Google consent screen
  2. GET /api/auth/google/callback  → exchange code → JWT → redirect to frontend
  3. POST /api/auth/refresh          → rotate refresh token
  4. POST /api/auth/logout           → clear refresh cookie
"""

import hashlib
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, verify_refresh_token
from app.db.models import PhoneOTP, User
from app.db.session import get_db

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

REFRESH_COOKIE = "refresh_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=False,  # set True in production
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
        path="/api/auth",
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/google")
async def google_login() -> RedirectResponse:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
@router.get("/callback")          # alias: matches GOOGLE_REDIRECT_URI=/api/auth/callback
async def google_callback(
    code: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    # 1. Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()

        # 2. Get user info
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    google_sub = userinfo["sub"]
    email = userinfo["email"]
    name = userinfo.get("name", email.split("@")[0])
    avatar_url = userinfo.get("picture")

    # 3. Upsert user
    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            google_sub=google_sub,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )
        db.add(user)
    else:
        user.name = name
        user.avatar_url = avatar_url

    await db.commit()
    await db.refresh(user)

    # 4. Issue JWT tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    # 5. Redirect to frontend with access token in URL (frontend stores in memory/localStorage)
    redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?access_token={access_token}",
        status_code=302,
    )
    _set_refresh_cookie(redirect, refresh_token)
    return redirect


@router.post("/refresh")
async def refresh_token(
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not refresh_token_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    try:
        user_id = verify_refresh_token(refresh_token_cookie)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Rotate refresh token
    new_access = create_access_token(str(user.id))
    new_refresh = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, new_refresh)

    return {"access_token": new_access, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/auth")
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
        "phone_verified": current_user.phone_verified,
        "profile_slug": current_user.profile_slug,
        "building_id": str(current_user.building_id) if current_user.building_id else None,
    }


# ---------------------------------------------------------------------------
# Phone OTP
# ---------------------------------------------------------------------------

OTP_EXPIRE_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 3
OTP_LOCK_MINUTES = 10


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def _generate_otp() -> str:
    return str(random.randint(100000, 999999))


class SendOTPRequest(BaseModel):
    phone_number: str


class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp: str


@router.post("/phone/send-otp")
async def send_otp(
    body: SendOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    now = datetime.now(timezone.utc)
    phone = body.phone_number.strip()

    # Check for recent unexpired OTP (resend cooldown)
    result = await db.execute(
        select(PhoneOTP)
        .where(PhoneOTP.phone_number == phone, PhoneOTP.is_used == False)  # noqa: E712
        .order_by(PhoneOTP.created_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Check lock
        if existing.locked_until and existing.locked_until > now:
            wait = int((existing.locked_until - now).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Locked. Try again in {wait}s",
            )
        # Cooldown check
        elapsed = (now - existing.created_at.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            remaining = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Wait {remaining}s before resending",
            )
        # Invalidate old OTP
        existing.is_used = True

    otp = _generate_otp()
    otp_record = PhoneOTP(
        phone_number=phone,
        otp_hash=_hash_otp(otp),
        expires_at=now + timedelta(minutes=OTP_EXPIRE_MINUTES),
    )
    db.add(otp_record)
    await db.commit()

    # Send OTP — mock mode logs to console
    if getattr(settings, "SMS_PROVIDER", "mock") == "mock" or not getattr(settings, "SMS_API_KEY", ""):
        print(f"[OTP MOCK] Phone: {phone}, OTP: {otp}")
    # else: integrate Vonage/Twilio here

    return {"message": f"OTP sent to {phone}"}


@router.post("/phone/verify")
async def verify_otp(
    body: VerifyOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    now = datetime.now(timezone.utc)
    phone = body.phone_number.strip()

    result = await db.execute(
        select(PhoneOTP)
        .where(PhoneOTP.phone_number == phone, PhoneOTP.is_used == False)  # noqa: E712
        .order_by(PhoneOTP.created_at.desc())
        .limit(1)
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="No OTP found for this number")

    # Check lock
    if record.locked_until and record.locked_until > now:
        wait = int((record.locked_until - now).total_seconds())
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Locked. Try again in {wait}s")

    # Check expiry
    if record.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=400, detail="OTP expired")

    # Check OTP
    if record.otp_hash != _hash_otp(body.otp):
        record.attempt_count += 1
        if record.attempt_count >= OTP_MAX_ATTEMPTS:
            record.locked_until = now + timedelta(minutes=OTP_LOCK_MINUTES)
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Success
    record.is_used = True
    current_user.phone_number = phone
    current_user.phone_verified = True
    await db.commit()

    return {"message": "Phone verified", "phone_number": phone}
