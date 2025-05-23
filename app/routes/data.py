from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate
from helper import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from helper import get_pg_connection, release_pg_connection

router = APIRouter()

@router.get("/toplist/")
async def get_toplist():

    conn = await get_pg_connection() 
    query = "SELECT username, online_time FROM users ORDER BY online_time DESC"
    result = await conn.fetch(query)
    await release_pg_connection(conn)

    return result
    


@router.get("/online/{channel}/")
async def get_channel_by_name(channel : str):

    conn = await get_pg_connection() 
    query = "SELECT u.username, u.username_html FROM users u, channels c WHERE u.channel_id = c.id AND  c.name = $1"
    result = await conn.fetch(query, channel)
    await release_pg_connection(conn)

    return result

@router.get("/online_by_id/{id}/")
async def get_channel_by_id(id : int):

    conn = await get_pg_connection() 
    query = "SELECT u.username, u.username_html FROM users u WHERE u.channel_id = $1"
    result = await conn.fetch(query, id)
    await release_pg_connection(conn)

    return result


@router.get("/channels/")
async def get_channel_by_id():

    conn = await get_pg_connection() 
    query = "SELECT id,name FROM channels"
    result = await conn.fetch(query)
    await release_pg_connection(conn)

    return result

    