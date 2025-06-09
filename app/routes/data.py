from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate
from db import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from typing import Optional

class UserFormData(BaseModel):
    username_html: Optional[str] = None
    name: Optional[str] = None
    tel: Optional[str] = None
    mail: Optional[str] = None
    fediverse_id: Optional[str] = None
    login_msg: Optional[str] = None
    logout_msg: Optional[str] = None



import re

router = APIRouter()

@router.get("/toplist/")
async def get_toplist():

    conn = await get_pg_connection() 
    query = "SELECT username, online_time FROM users ORDER BY online_time DESC"
    result = await conn.fetch(query)
    await release_pg_connection(conn)

    return result
    


@router.get("/online/")
async def get_current_channel(request : Request):

    conn = await get_pg_connection() 
    query = "SELECT u.username, u.username_html FROM users u, users u2 WHERE u.channel_id = u2.channel_id AND u.token != '' AND u2.id = $1"
    result = await conn.fetch(query, request.state.user_id)
    await release_pg_connection(conn)

    return result

@router.get("/online/{channel}/")
async def get_channel_by_name(channel : str):

    conn = await get_pg_connection() 
    query = "SELECT u.username, u.username_html FROM users u, channels c WHERE u.channel_id = c.id AND u.token != '' AND c.name = $1"
    result = await conn.fetch(query, channel)
    await release_pg_connection(conn)

    return result

@router.get("/online_by_channel_id/{id}/")
async def get_channel_by_id(id : int):

    conn = await get_pg_connection() 
    query = "SELECT u.username, u.username_html FROM users u WHERE u.token != '' AND u.channel_id = $1"
    result = await conn.fetch(query, id)
    await release_pg_connection(conn)

    return result


@router.get("/channels/")
async def get_channels():
    conn = await get_pg_connection() 
    query = "SELECT id,name FROM channels"
    result = await conn.fetch(query)
    await release_pg_connection(conn)
    return result




# also check admin functions in userdb.py
@router.get("/get_user_info/")
async def get_user_info(request : Request):
    conn = await get_pg_connection()
    query = """
        SELECT id, username, username_html, name, tel,mail, fediverse_id, login_msg, logout_msg,
        online_time, created, last_posted, last_login, login_count, remove_on_logout, 
        admin, channel_id
        FROM users 
        WHERE id = $1
    """
    result = await conn.fetchrow(query, request.state.user_id)
    await release_pg_connection(conn)
    return result


@router.post("/set_user_info/")
async def set_user_info(data : UserFormData, request : Request):
    conn = await get_pg_connection()

    query = """
        UPDATE users
        SET 
            username_html = COALESCE($1, username_html),
            name          = COALESCE($2, name),
            tel           = COALESCE($3, tel),
            mail          = COALESCE($4, mail),
            fediverse_id  = COALESCE($5, fediverse_id),
            login_msg     = COALESCE($6, login_msg),
            logout_msg    = COALESCE($7, logout_msg)
        WHERE id = $8
    """

    await conn.execute(query,
        data.username_html,
        data.name,
        data.tel,
        data.mail,
        data.fediverse_id,
        data.login_msg,
        data.logout_msg,
        request.state.user_id
    )
    await release_pg_connection(conn)


@router.post("/change_name_color/{fromhex}/{tohex}/")
async def set_name_color(fromhex: str, tohex: str, request: Request):
    # Validate hex color format
    if not re.fullmatch(r"[0-9a-fA-F]{6}", fromhex) or not re.fullmatch(r"[0-9a-fA-F]{6}", tohex):
        raise HTTPException(status_code=400, detail="Hex color codes must be 6-digit hexadecimal strings.")

    # Convert hex to RGB
    def hex_to_rgb(hex_str):
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

    # Convert RGB to hex
    def rgb_to_hex(rgb):
        return ''.join(f"{c:02x}" for c in rgb)

    # Interpolate color between start and end
    def interpolate_color(start, end, factor):
        return tuple(int(start[i] + (end[i] - start[i]) * factor) for i in range(3))

    # Apply gradient to username
    def apply_gradient(username, fromhex, tohex):
        start_rgb = hex_to_rgb(fromhex)
        end_rgb = hex_to_rgb(tohex)
        result = ""
        length = len(username)
        for i, char in enumerate(username):
            factor = i / max(length - 1, 1)
            color = interpolate_color(start_rgb, end_rgb, factor)
            hex_color = rgb_to_hex(color)
            result += f'<font color="#{hex_color}">{char}</font>'
        return "<b>" + result + "</b>"

    # DB logic
    conn = await get_pg_connection()
    try:
        query = "SELECT username FROM users WHERE id = $1"
        result = await conn.fetchrow(query, request.state.user_id)

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        username = result["username"]
        username_html = apply_gradient(username, fromhex, tohex)

        update_query = "UPDATE users SET username_html = $1 WHERE id = $2"
        await conn.execute(update_query, username_html, request.state.user_id)

        return {"success": True}
    finally:
        await release_pg_connection(conn)