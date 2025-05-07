from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate
from helper import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from helper import get_pg_connection, release_pg_connection

router = APIRouter()




@router.get("/")
async def get_toplist():

    conn = await get_pg_connection() 
    query = "SELECT username, online_time FROM users ORDER BY online_time DESC"
    result = await conn.fetch(query)
    await release_pg_connection(conn)

    return result
    