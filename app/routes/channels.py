from typing import Annotated
from fastapi import FastAPI, UploadFile, File, HTTPException,APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate
from db import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import json

router = APIRouter()


class SendMessageRequest(BaseModel):
    message: str



#new 
@router.post("/create_channel/")
async def create_channel(name : str, password: str, request: Request):
    conn = await get_pg_connection()
    try:

        query = """
            INSERT INTO channels (name, always_available, password, owner)
            VALUES ($1, false, $2, $3)
            ON CONFLICT DO NOTHING
            RETURNING id
        """
        channel_id = await conn.fetchval(query, name, password, request.state.user_id)

        query = """
            INSERT INTO channel_members (user_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """
        await conn.execute(query, request.state.user_id, channel_id)

        await conn.execute(
            f"NOTIFY whisper_{request.state.user_id}, 'add {channel_id}'"
        )
    finally:
        await release_pg_connection(conn)

    return {"result": True}



#new 
@router.post("/add_channel/{channel_id}/")
async def add_channel_by_id(channel_id: int, request: Request):
    conn = await get_pg_connection()
    try:
        query = """
            INSERT INTO channel_members (user_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """
        await conn.execute(query, request.state.user_id, channel_id)

        await conn.execute(
            f"NOTIFY whisper_{request.state.user_id}, 'add {channel_id}'"
        )
    finally:
        await release_pg_connection(conn)

    return {"result": True}

#new 
@router.post("/remove_channel/{channel_id}/")
async def remove_channel_by_id(channel_id: int, request: Request):
    conn = await get_pg_connection()
    try:
        query = """
            DELETE FROM channel_members
            WHERE user_id = $1
            AND channel_id = $2
        """
        await conn.execute(query, request.state.user_id, channel_id)

        await conn.execute(
            f"NOTIFY whisper_{request.state.user_id}, 'remove {channel_id}'"
        )
    finally:
        await release_pg_connection(conn)

    return {"result": True}



