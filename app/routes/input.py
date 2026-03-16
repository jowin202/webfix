from typing import Annotated
from fastapi import FastAPI, UploadFile, File, HTTPException,APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate
from db import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional

import json

router = APIRouter()


class SendMessageRequest(BaseModel):
    message: str
    channel_id: Optional[int] = None

@router.post("/")
async def write_text(data: SendMessageRequest, request: Request):
    conn = await get_pg_connection()
    query = """
        SELECT username, channel_id, last_posted,id,
        CASE 
            WHEN muted_until = 'infinity'::timestamp 
                THEN 9223372036854775807
            WHEN muted_until = '-infinity'::timestamp 
                OR muted_until - NOW() < INTERVAL '0 seconds'
                THEN 0
            ELSE EXTRACT(EPOCH FROM (muted_until - NOW()))
        END AS muted_seconds
        FROM users 
        WHERE id = $1
    """
    result = await conn.fetchrow(query, request.state.user_id)


    if result:
        # timeout prevention
        query = """
            UPDATE users
            SET online_time = online_time + EXTRACT(EPOCH FROM (NOW() - last_posted))::int,
            last_posted = NOW()
            WHERE id = $1
        """
        await conn.execute(query, request.state.user_id)

        id = result['id']
        channel_id = int(result['channel_id']) if result else -1
        muted_seconds = result['muted_seconds']

        # Allow clients to choose a target channel if the user can access it.
        if data.channel_id is not None:
            can_use_channel = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM channels c
                    WHERE c.id = $1
                    AND (
                        c.always_available = true
                        OR EXISTS (
                            SELECT 1
                            FROM channel_members cm
                            WHERE cm.user_id = $2
                            AND cm.channel_id = c.id
                        )
                    )
                )
                """,
                int(data.channel_id),
                request.state.user_id,
            )
            if can_use_channel:
                channel_id = int(data.channel_id)
        
        if muted_seconds <= 0:
            payload = json.dumps({
            "username": result['username'],
            "message": data.message,
            "channel": channel_id
            })
            quoted_payload = await conn.fetchval("SELECT quote_literal($1)", payload)
            await conn.execute(f"NOTIFY channel_{channel_id}, {quoted_payload}")
        else:
            await conn.execute(f"NOTIFY whisper_{id}, '{json.dumps({'cat': 'statusmsg', 'username': '', 'msg': 'You are muted for ' + str(int(muted_seconds)) + ' seconds.'})}'")


    await release_pg_connection(conn)
    return {"status": "notification sent", "message": data.message}



@router.post("/wh")
async def whisper(to_username: str, message: str, request: Request):
    from_name = ""
    to_id = -1

    conn = await get_pg_connection()
    query = """
        SELECT username, last_posted,
        CASE 
            WHEN muted_until = 'infinity'::timestamp 
                THEN 9223372036854775807
            WHEN muted_until = '-infinity'::timestamp 
                OR muted_until - NOW() < INTERVAL '0 seconds'
                THEN 0
            ELSE EXTRACT(EPOCH FROM (muted_until - NOW()))
        END AS muted_seconds
        FROM users 
        WHERE id = $1
    """
    result = await conn.fetchrow(query, request.state.user_id)

    if result:
        from_name = result['username']
        muted_seconds = result['muted_seconds']
        query = """
            UPDATE users
            SET online_time = online_time + EXTRACT(EPOCH FROM (NOW() - last_posted))::int,
            last_posted = NOW()
            WHERE id = $1
        """
        await conn.execute(query, request.state.user_id)

        if muted_seconds <= 0:
            query = """
                SELECT id
                FROM users 
                WHERE username = $1
            """
            result = await conn.fetchrow(query, to_username)
            if result:
                to_id = result['id']
                await conn.execute(f"NOTIFY whisper_{to_id}, '{json.dumps({'cat': 'whisper', 'username': from_name, 'msg': message})}'")
            else:
                await conn.execute(
                    f"NOTIFY whisper_{request.state.user_id}, '{json.dumps({'cat': 'statusmsg', 'msg': f'User {to_username} not found.'})}'"
                )

    await release_pg_connection(conn)
    return {"status": "notification sent", "message": message}

