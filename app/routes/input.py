from typing import Annotated
from fastapi import FastAPI, UploadFile, File, HTTPException,APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate
from helper import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import json

router = APIRouter()


CHANNEL = "mynotifications"


@router.post("/")
async def write_text(message: str, request: Request):
    conn = await get_pg_connection()
    query = """
        SELECT username, last_posted
        FROM users 
        WHERE id = $1
    """
    result = await conn.fetchrow(query, request.state.user_id)

    query = """
        UPDATE users
        SET online_time = online_time + EXTRACT(EPOCH FROM (NOW() - last_posted))::int,
        last_posted = NOW()
        WHERE id = $1
    """
    await conn.execute(query, request.state.user_id)

    payload = json.dumps({
    "username": result['username'],
    "message": message
    })
    quoted_payload = await conn.fetchval("SELECT quote_literal($1)", payload)
    await conn.execute(f"NOTIFY {CHANNEL}, {quoted_payload}")

    await release_pg_connection(conn)
    return {"status": "notification sent", "message": message}



@router.post("/wh")
async def whisper(to_username: str, message: str, request: Request):
    from_name = ""
    to_id = -1

    conn = await get_pg_connection()
    query = """
        SELECT username, last_posted
        FROM users 
        WHERE id = $1
    """
    result = await conn.fetchrow(query, request.state.user_id)
    from_name = result['username']

    query = """
        UPDATE users
        SET online_time = online_time + EXTRACT(EPOCH FROM (NOW() - last_posted))::int,
        last_posted = NOW()
        WHERE id = $1
    """
    await conn.execute(query, request.state.user_id)


    query = """
        SELECT id
        FROM users 
        WHERE username = $1
    """
    result = await conn.fetchrow(query, to_username)
    try:
        to_id = result['id']
        await conn.execute(f"NOTIFY whisper_{to_id}, '{from_name} whispers: {message}'")
    except:
        pass
    finally:
        await release_pg_connection(conn)
    
    # todo error message
    return {"status": "notification sent", "message": message}


