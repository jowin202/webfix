from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate, calc_hmac
from db import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from typing import Dict, Any, List
from typing import Optional
from settings import SettingsManager



router = APIRouter()


class SetUserRequest(BaseModel):
    name: Optional[str] = None
    tel: Optional[str] = None
    mail: Optional[str] = None
    fediverse_id: Optional[str] = None
    is_activated: Optional[bool] = None
    password: Optional[str] = None
    visible: Optional[bool] = None
    

manager = SettingsManager()

#TODO: IP
@router.get("/get_user_by_id/")
async def get_user_by_id(id : int):
    conn = await get_pg_connection()
    query = """
        SELECT id, username, username_html,name,tel,mail,fediverse_id,
        is_activated, online_time, failed_attempts, created,last_posted, last_login,
        login_count, remove_on_logout, visible, admin, channel_id
        FROM users 
        WHERE id = $1
    """
    result = await conn.fetchrow(query, id)
    return result

@router.get("/get_user_by_name/")
async def get_user_by_name(username : str):
    conn = await get_pg_connection()
    query = """
        SELECT id, username, username_html,name,tel,mail,fediverse_id,
        is_activated, online_time, failed_attempts, created,last_posted, last_login,
        login_count, remove_on_logout, visible, admin, channel_id
        FROM users 
        WHERE LOWER(username) = LOWER($1)
    """
    result = await conn.fetchrow(query, username)
    return result


#password
@router.put("/set_user/{id}/")
async def update_user_by_id(id : int, data: SetUserRequest):
    conn = await get_pg_connection()

    user = await conn.fetchrow("SELECT id FROM users WHERE id = $1", id)
    if not user:
        raise HTTPException(status_code=404, detail="User with given ID not found")

    password = calc_hmac(data.password) if data.password else None
    await conn.execute("""
        UPDATE users
        SET 
            name = COALESCE($1, name),
            tel = COALESCE($2, tel),
            mail = COALESCE($3, mail),
            fediverse_id = COALESCE($4, fediverse_id),
            is_activated = COALESCE($5, is_activated),
            visible = COALESCE($6, visible),
            password = COALESCE($7, password)
        WHERE id = $8
    """, data.name, data.tel, data.mail, data.fediverse_id, data.is_activated, data.visible, password, id)

    return {"status": "updated", "id": id}


@router.put("/set_user_by_name/{username}/")
async def update_user_by_name(username : str, data: SetUserRequest):
    conn = await get_pg_connection()

    user = await conn.fetchrow("SELECT id FROM users WHERE LOWER(username) = LOWER($1)", username)
    if not user:
        raise HTTPException(status_code=404, detail="User with given username not found")

    password = calc_hmac(data.password) if data.password else None
    await conn.execute("""
        UPDATE users
        SET 
            name = COALESCE($1, name),
            tel = COALESCE($2, tel),
            mail = COALESCE($3, mail),
            fediverse_id = COALESCE($4, fediverse_id),
            is_activated = COALESCE($5, is_activated),
            visible = COALESCE($6, visible),
            password = COALESCE($7, password)
        WHERE LOWER(username) = LOWER($8)
    """, data.name, data.tel, data.mail, data.fediverse_id, data.is_activated, data.visible, password, username)

    return {"status": "updated", "username": username}
