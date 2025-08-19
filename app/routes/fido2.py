from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os, secrets

from webauthn import (
    verify_registration_response,
    verify_authentication_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

# ============ CONFIG ============
RP_ID = os.getenv("FIDO2_RP_ID", "localhost")
RP_NAME = os.getenv("FIDO2_RP_NAME", "Webfix")
ORIGIN = os.getenv("FIDO2_ORIGIN", "http://localhost")

USERS: Dict[str, Dict[str, Any]] = {}
CHALLENGES: Dict[str, str] = {}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BeginPayload(BaseModel):
    username: str
    display_name: Optional[str] = None

class FinishPayload(BaseModel):
    username: str
    credential: Dict[str, Any]
    
def _new_challenge() -> bytes:
    return secrets.token_bytes(32)

# -------- Registration --------
@app.post("/register/begin")
def register_begin(body: BeginPayload):
    username = body.username.strip().lower()
    challenge = _new_challenge()
    CHALLENGES[username] = challenge
    return {
        "publicKey": {
            "rp": {"id": RP_ID, "name": RP_NAME},
            "user": {
                "id": bytes_to_base64url(username.encode()),
                "name": username,
                "displayName": body.display_name or username,
            },
            "challenge": bytes_to_base64url(challenge),
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},    # ES256, ECDSA with SHA-256 on P-256 curve
                {"type": "public-key", "alg": -257},  # RS256, RSASSA-PKCS1-v1_5 with SHA-256
            ],
        }
    }

@app.post("/register/verify")
def register_verify(body: FinishPayload):
    username = body.username.strip().lower()
    challenge = CHALLENGES.get(username)
    if challenge is None:
        raise HTTPException(400, "No challenge")

    try:
        result = verify_registration_response(
            credential=body.credential,
            expected_challenge=challenge,
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            require_user_verification=True,
        )
    except Exception as e:
        raise HTTPException(400, f"verify failed: {e}")

    cred = {
        "id": result.credential_id,
        "public_key": result.credential_public_key,
        "sign_count": result.sign_count,
    }
    USERS.setdefault(username, {"username": username, "credentials": []})["credentials"].append(cred)
    CHALLENGES.pop(username, None)
    return {"ok": True}



# -------- Authentication --------
@app.post("/login/begin")
def login_begin(body: BeginPayload):
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

@app.post("/login/verify")
def login_verify(body: FinishPayload):
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
