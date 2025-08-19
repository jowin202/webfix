from fastapi import Depends, FastAPI, HTTPException, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os, secrets

from security import verify_token
from db import get_pg_connection, release_pg_connection

from webauthn import (
    verify_registration_response,
    verify_authentication_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

from settings import SettingsManager



router = APIRouter()
manager = SettingsManager()


# ============ CONFIG ============
RP_ID = os.getenv("FIDO2_RP_ID", "localhost")
RP_NAME = os.getenv("FIDO2_RP_NAME", "Webfix")
ORIGIN = os.getenv("FIDO2_ORIGIN", "http://localhost")

USERS: Dict[str, Dict[str, Any]] = {}
CHALLENGES: Dict[str, str] = {}


class BeginPayload(BaseModel):
    username: str

class FinishPayload(BaseModel):
    credential: Dict[str, Any]
    
def _new_challenge() -> bytes:
    return secrets.token_bytes(32)

# -------- Registration --------
@router.post("/register/begin")
async def register_begin(request: Request, token: str = Depends(verify_token)):
    challenge = _new_challenge()
    id = request.state.user_id
    username = ""

    exclude = []
    try:
        conn = await get_pg_connection()
        user = await conn.fetchrow("SELECT username FROM users WHERE id=$1", id)
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        username = user['username']
        
        
        # save challenge
        await conn.execute(
            """
            INSERT INTO webauthn_challenges (user_id, challenge)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET challenge=EXCLUDED.challenge, valid_from=EXCLUDED.valid_from
            """,
            id, bytes_to_base64url(challenge))

        # list credentials
        credential_list = await conn.fetch(
            "SELECT credential_id, public_key, sign_count FROM webauthn_credentials WHERE user_id=$1",id)

        exclude = [
            {
                "type": "public-key",
                "id": bytes_to_base64url(bytes(c["credential_id"])),
            }
            for c in credential_list
        ]

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if conn:
            await release_pg_connection(conn)
            
    return {
        "publicKey": {
            "rp": {"id": RP_ID, "name": RP_NAME},
            "user": {
                "id": bytes_to_base64url(username.encode()),
                "name": username,
                "displayName": username,
            },
            "challenge": bytes_to_base64url(challenge),
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},    # ES256, ECDSA with SHA-256 on P-256 curve
                {"type": "public-key", "alg": -257},  # RS256, RSASSA-PKCS1-v1_5 with SHA-256
            ],
            "excludeCredentials": exclude,
        }
    }

@router.post("/register/verify")
async def register_verify(body: FinishPayload, request: Request, token: str = Depends(verify_token)):
    id = request.state.user_id
    challenge = None
    
    try:
        conn = await get_pg_connection()
        row = await conn.fetchrow("""
            SELECT challenge
            FROM webauthn_challenges
            WHERE user_id = $1
            AND valid_from >= NOW() - ($2 || ' seconds')::interval
            """, id, str(300))
        if not row:
            raise HTTPException(400, "No challenge")
        
        challenge = bytes(base64url_to_bytes(row['challenge'])) # was converted earlier

        # delete
        await conn.execute("DELETE FROM webauthn_challenges WHERE user_id=$1", id)

        # verify result (or exception)
        result = verify_registration_response(
            credential=body.credential,              # raw dict from browser
            expected_challenge=challenge,            # raw bytes
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            require_user_verification=True,
        )

        await conn.execute(
            """
            INSERT INTO webauthn_credentials (user_id, credential_id, public_key, sign_count)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (credential_id) DO NOTHING
            """,
            id, result.credential_id, result.credential_public_key, int(result.sign_count)
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if conn:
            await release_pg_connection(conn)

    return {"ok": True}
        


# -------- Authentication --------
@router.post("/login/begin")
async def login_begin(body: BeginPayload):
    username = body.username.strip().lower()
    user = USERS.get(username)
    if not user:
        raise HTTPException(404, "User not found")

    # generate and store raw challenge
    challenge = _new_challenge()
    CHALLENGES[username] = challenge 

    # return encoded challenge
    return {
        "publicKey": {
            "challenge": bytes_to_base64url(challenge), 
            "rpId": RP_ID,
            "allowCredentials": [
                {"type": "public-key", "id": bytes_to_base64url(c["id"])}
                for c in user["credentials"]
            ],
        }
    }

@router.post("/login/verify")
async def login_verify(body: FinishPayload):
    username = body.username.strip().lower()

    challenge = CHALLENGES.get(username)   # raw bytes
    if not challenge:
        raise HTTPException(400, "No challenge")

    user = USERS.get(username)
    if not user:
        raise HTTPException(404, "User not found")

    # decode incoming credential ID to bytes
    try:
        incoming_id = base64url_to_bytes(body.credential.get("id"))
    except Exception:
        raise HTTPException(400, "Invalid credential id format")

    stored = next((c for c in user["credentials"] if c["id"] == incoming_id), None)
    if not stored:
        raise HTTPException(400, "Unknown credential id")

    try:
        result = verify_authentication_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=stored["public_key"],
            credential_current_sign_count=stored["sign_count"],
            require_user_verification=False,
        )
    except Exception as e:
        raise HTTPException(400, f"verify failed: {e}")

    stored["sign_count"] = result.new_sign_count
    CHALLENGES.pop(username, None)
    return {"ok": True, "username": username}
