from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import OAuthClient
from app.security import issue_access_token, verify_secret

router = APIRouter(tags=["oauth"])


@router.post("/oauth/token")
def issue_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    db: Session = Depends(get_db),
):
    if grant_type != "client_credentials":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    client = db.get(OAuthClient, client_id)
    if not client or not verify_secret(client_secret, client.client_secret_hash):
        raise HTTPException(status_code=401, detail="invalid_client")

    access_token, expires_in = issue_access_token(client_id)
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
    }
