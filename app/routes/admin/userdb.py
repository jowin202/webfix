from fastapi import APIRouter, HTTPException
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
    login_msg: Optional[str] = None
    logout_msg: Optional[str] = None
    fediverse_id: Optional[str] = None
    is_activated: Optional[bool] = None
    password: Optional[str] = None
    visible: Optional[bool] = None
    

manager = SettingsManager()



@router.get("/get_all_users/")
async def get_all_users():
    conn = await get_pg_connection()
    try:
        query = """
            SELECT id, username, username_html, admin, kicked_until, muted_until
            FROM users
            ORDER BY id
        """
        result = await conn.fetch(query)
        return result
    finally:
        await release_pg_connection(conn)


# also check function in data.py
#TODO: IP
@router.get("/get_user_by_id/")
async def get_user_by_id(id : int):
    conn = await get_pg_connection()
    try:
        query = """
            SELECT id, username, username_html,name,tel,mail,fediverse_id, login_msg, logout_msg,
            is_activated, online_time, failed_attempts, created,last_posted, last_login,
            login_count, remove_on_logout, visible, kicked_until, muted_until, admin, channel_id
            FROM users
            WHERE id = $1
        """
        result = await conn.fetchrow(query, id)
        return result
    finally:
        await release_pg_connection(conn)

@router.put("/set_user/{id}/")
async def update_user_by_id(id : int, data: SetUserRequest):
    conn = await get_pg_connection()
    try:
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
                password = COALESCE($7, password),
                login_msg = COALESCE($8, login_msg),
                logout_msg = COALESCE($9, logout_msg)
            WHERE id = $10
        """, data.name, data.tel, data.mail, data.fediverse_id, data.is_activated, data.visible, password, data.login_msg, data.logout_msg, id)

        return {"status": "updated", "id": id}
    finally:
        await release_pg_connection(conn)

