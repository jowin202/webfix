from fastapi import Depends, FastAPI, HTTPException, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os, secrets

from security import verify_token
from helper import calc_hmac, token_generate
from db import get_pg_connection, release_pg_connection

import json
import webauthn
from webauthn import (
    verify_registration_response,
    verify_authentication_response
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

from settings import SettingsManager



router = APIRouter()
manager = SettingsManager()


# ============ CONFIG ============
RP_ID = os.getenv("FIDO2_RP_ID", "localhost")
RP_NAME = os.getenv("FIDO2_RP_NAME", "Webfix")
ORIGIN = os.getenv("FIDO2_ORIGIN", "http://localhost")

class RegisterBeginPayload(BaseModel):
    password: str

class BeginPayload(BaseModel):
    username: str

class FinishPayload(BaseModel):
    credential: Dict[str, Any]
    name: str

class FinishLoginPayload(BaseModel):
    credential: Dict[str, Any]
    username: str
    
def _new_challenge() -> bytes:
    return secrets.token_bytes(32)

# -------- Registration --------
@router.post("/register/begin")
async def register_begin(data: RegisterBeginPayload, request: Request, token: str = Depends(verify_token)):
    challenge = _new_challenge()
    id = request.state.user_id
    username = ""
    password = calc_hmac(data.password)

    exclude = []
    try:
        conn = await get_pg_connection()
        user = await conn.fetchrow("SELECT username FROM users WHERE id=$1 AND password=$2", id, password)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        username = user['username']
        
        
        # store challenge
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
        raise HTTPException(status_code=e.status_code, detail=str(e))
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
            """, id, str(manager.get_setting("fido2_challenge_valid_time")))
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
            INSERT INTO webauthn_credentials (user_id, name, credential_id, public_key, sign_count)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (credential_id) DO NOTHING
            """,
            id, body.name, result.credential_id, result.credential_public_key, int(result.sign_count)
        )
    
    except Exception as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    finally:
        if conn:
            await release_pg_connection(conn)

    return {"ok": True}
        


# -------- Authentication --------
@router.post("/login/begin")
async def login_begin(body: BeginPayload):
    username = body.username.strip().lower()
    challenge = _new_challenge()
    credential_list = []

    try:
        conn = await get_pg_connection()
        result = await conn.fetchrow("SELECT u.id AS id FROM users u WHERE u.username=$1", username)
        if not result:
            raise HTTPException(404, "User not found")
        id = result['id']
        
        # list credentials
        credential_list = await conn.fetch(
            "SELECT credential_id, public_key, sign_count FROM webauthn_credentials WHERE user_id=$1",id)
        
        if not credential_list:
            raise HTTPException(404, "No credentials for user")
        
        # store challenge
        await conn.execute(
            """
            INSERT INTO webauthn_challenges (user_id, challenge)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET challenge=EXCLUDED.challenge, valid_from=EXCLUDED.valid_from
            """,
            id, bytes_to_base64url(challenge))
        
    except Exception as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    finally:
        if conn:
            await release_pg_connection(conn)
    

    # return encoded challenge
    return {
        "publicKey": {
            "challenge": bytes_to_base64url(challenge), 
            "rpId": RP_ID,
            "allowCredentials": [
                {"type": "public-key", "id": bytes_to_base64url(bytes(c["credential_id"]))}
                for c in credential_list
            ],
        }
    }


@router.post("/login/verify")
async def login_verify(body: FinishLoginPayload):
    username = body.username.strip().lower()
    id = -1
    
    try:
        conn = await get_pg_connection()
        result = await conn.fetchrow("SELECT u.id AS id FROM users u WHERE u.username=$1", username)
        if not result:
            raise HTTPException(404, "Unknown username")
        id = result['id']

        row = await conn.fetchrow("""
            SELECT challenge
            FROM webauthn_challenges
            WHERE user_id = $1
            AND valid_from >= NOW() - ($2 || ' seconds')::interval
            """, id, str(manager.get_setting("fido2_challenge_valid_time")))
        
        if not row:
            raise HTTPException(400, "No challenge")
        
        challenge = bytes(base64url_to_bytes(row['challenge'])) # was converted earlier

        # delete
        await conn.execute("DELETE FROM webauthn_challenges WHERE user_id=$1", id)

        try:
            incoming_id = base64url_to_bytes(body.credential.get("id"))
        except Exception:
            raise HTTPException(422, "Invalid credential id format")

        cred = await conn.fetchrow(
            "SELECT credential_id, public_key, sign_count FROM webauthn_credentials WHERE user_id=$1 AND credential_id=$2",
            id, incoming_id
        )
        
        if not cred:
            raise HTTPException(400, "Unknown credential id")
        

        result = verify_authentication_response(
            credential=body.credential,                  # raw dict from browser
            expected_challenge=challenge,                # raw bytes
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=bytes(cred["public_key"]),
            credential_current_sign_count=int(cred["sign_count"]),
            require_user_verification=False,
        )
        
        await conn.execute(
            """
            UPDATE webauthn_credentials
            SET sign_count=$3, last_used_at=now()
            WHERE user_id=$1 AND credential_id=$2
            """,
            id, incoming_id, int(result.new_sign_count)
        )

    except webauthn.helpers.exceptions.InvalidAuthenticationResponse as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    finally:
        if conn:
            await release_pg_connection(conn)


    # TODO: make this better
    # Login procedure from login.py copied
    valid = False
    token = token_generate()
    login_msg = ""
    channel_id = 1
    try:
        conn = await get_pg_connection()
        query = '''
            SELECT id, is_activated, login_msg
            FROM users 
            WHERE LOWER(username) = LOWER($1)
        '''
        result = await conn.fetchrow(query, username)
        user_id = result['id']
        login_msg = result['login_msg']

        if not manager.get_setting("mandatory_user_verification") or result['is_activated']:
            valid = True
            query = '''
                UPDATE users 
                SET token = $1,
                last_login = NOW(),
                last_posted = NOW(),
                login_count = login_count+1,
                failed_attempts = 0
                WHERE LOWER(username) = LOWER($2)
            '''
            await conn.execute(query, token, username)
            
            # logout if logged in
            await conn.execute(f"NOTIFY channel_{channel_id}, '{json.dumps({'cat': 'userlogin', 'username': username, 'msg': login_msg})}'")
            await conn.execute(f"NOTIFY whisper_{user_id}, '{json.dumps({'cat': 'statusmsg', 'msg': 'double login'})}'")
            await conn.execute(f"NOTIFY whisper_{user_id}, 'exit'")


    except:
        valid = False
    finally:
        if conn:
            await release_pg_connection(conn)

    if not valid:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    return {"access_token": token}







@router.get("/credentials/")
async def get_credentials(request : Request, token: str = Depends(verify_token)):
    
    conn = await get_pg_connection() 
    query = '''
        SELECT id,name,created_at,last_used_at,sign_count FROM webauthn_credentials 
        WHERE user_id = $1
    '''
    result = await conn.fetch(query, request.state.user_id)
    await release_pg_connection(conn)

    return result

@router.delete("/credentials/{id}/")
async def delete_credential(request : Request, id : int, token: str = Depends(verify_token)):
    
    conn = await get_pg_connection() 
    query = '''
        DELETE FROM webauthn_credentials
        WHERE user_id = $1 AND id = $2
    '''
    result = await conn.fetch(query, request.state.user_id, id)
    await release_pg_connection(conn)

    return True