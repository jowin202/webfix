from typing import Annotated
from fastapi import FastAPI, UploadFile, File, HTTPException,APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate
from helper import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


router = APIRouter()


CHANNEL = "mynotifications"


@router.post("/")
async def send_notification(message: str, request: Request):
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

    

    await conn.execute(f"NOTIFY {CHANNEL}, '{result['username']}: {message}'")
    await release_pg_connection(conn)
    return {"status": "notification sent", "message": message}