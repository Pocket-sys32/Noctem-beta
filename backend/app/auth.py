"""JWT verification for Supabase Auth tokens."""

from __future__ import annotations

import os
from fastapi import Header, HTTPException


async def get_user_id(authorization: str = Header(...)) -> str:
    """Extract user_id from Supabase JWT via the backend's service client.

    For MVP we decode the JWT using the Supabase Python client.
    The dashboard sends `Authorization: Bearer <access_token>`.
    """
    from app.db import get_supabase

    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")

    sb = get_supabase()
    try:
        user_resp = sb.auth.get_user(token)
        if user_resp and user_resp.user:
            return str(user_resp.user.id)
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid or expired token")
