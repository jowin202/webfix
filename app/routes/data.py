from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate, calc_hmac
from db import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


from settings import SettingsManager

from bs4 import BeautifulSoup
import bleach


ALLOWED_TAGS = ["b", "i", "u", "em", "strong", "span", "br", "s", "font"]

ALLOWED_ATTRIBUTES = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "font": ["color"],
    "span": ["style"],
}




from typing import Optional

class UserFormData(BaseModel):
    username_html: Optional[str] = None
    name: Optional[str] = None
    tel: Optional[str] = None
    mail: Optional[str] = None
    fediverse_id: Optional[str] = None
    login_msg: Optional[str] = None
    logout_msg: Optional[str] = None
    password: Optional[str] = None



import re

router = APIRouter()
manager = SettingsManager()

@router.get("/toplist/")
async def get_toplist():

    conn = await get_pg_connection() 
    query = "SELECT username, online_time FROM users ORDER BY online_time DESC"
    result = await conn.fetch(query)
    await release_pg_connection(conn)

    return result
    


# TODO: online vs offline vs busy ... status = 1 is online
@router.get("/users/")
async def get_users(request : Request):

    conn = await get_pg_connection() 
    query = "SELECT u.id, u.username, u.username_html, 1 as status FROM users u WHERE u.token != ''"
    result = await conn.fetch(query)
    await release_pg_connection(conn)

    return result


@router.get("/users_by_channel_id/{id}/")
async def get_users_by_channel_id(id : int):

    conn = await get_pg_connection()
    query = """
        SELECT u.username, u.username_html
        FROM users u
        WHERE u.token != ''
        AND (
            EXISTS (
                SELECT 1 FROM channels c
                WHERE c.id = $1
                AND c.always_available = true
            )
            OR EXISTS (
                SELECT 1 FROM channel_members cm
                WHERE cm.channel_id = $1
                AND cm.user_id = u.id
            )
        )
    """
    result = await conn.fetch(query, id)
    await release_pg_connection(conn)

    return result


@router.get("/channels/")
async def get_channels(request: Request):
    conn = await get_pg_connection() 
    query = """
        SELECT c.id, c.name
        FROM channels c
        WHERE c.always_available = true
           OR c.id = 1
           OR EXISTS (
                SELECT 1
                FROM channel_members cm
                WHERE cm.channel_id = c.id
                AND cm.user_id = $1
           )
        ORDER BY c.id
    """
    result = await conn.fetch(query, request.state.user_id)
    await release_pg_connection(conn)
    return result




# also check admin functions in userdb.py
@router.get("/get_user_info/")
async def get_user_info(request : Request):
    conn = await get_pg_connection()
    query = """
        SELECT id, username, username_html, name, tel,mail, fediverse_id, login_msg, logout_msg,
        online_time, created, last_posted, last_login, login_count, remove_on_logout, 
        admin
        FROM users 
        WHERE id = $1
    """
    result = await conn.fetchrow(query, request.state.user_id)
    await release_pg_connection(conn)
    return result


@router.post("/set_user_info/")
async def set_user_info(data : UserFormData, request : Request):

    # if password too short, then no db connection is made
    if data.password and len(data.password) < manager.get_setting("pw_min_len"):
        raise HTTPException(status_code=400, detail="Password too short")

    conn = await get_pg_connection()

    change_pw = False
    if data.password:
        change_pw = True
        data.password = calc_hmac(data.password)


    result = await conn.fetchrow("SELECT username FROM users WHERE id = $1", request.state.user_id)
    if not result:
        await release_pg_connection(conn)
        raise HTTPException(status_code=404, detail="User not found")

    current_username = result["username"]

    # Step 4: Decide whether to update username_html
    error_at_html_user = False
    clean_username_html = None
    if data.username_html:
        sanitized_html = bleach.clean(data.username_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
        stripped_html = BeautifulSoup(sanitized_html, "html.parser").get_text()
        if stripped_html == current_username:
            clean_username_html = sanitized_html
        else:
            error_at_html_user = True

    query = """
        UPDATE users
        SET 
            username_html = COALESCE($1, username_html),
            name          = COALESCE($2, name),
            tel           = COALESCE($3, tel),
            mail          = COALESCE($4, mail),
            fediverse_id  = COALESCE($5, fediverse_id),
            login_msg     = COALESCE($6, login_msg),
            logout_msg    = COALESCE($7, logout_msg),
            password      = COALESCE($8, password)
        WHERE id = $9
    """

    await conn.execute(query,
        clean_username_html,
        data.name,
        data.tel,
        data.mail,
        data.fediverse_id,
        data.login_msg,
        data.logout_msg,
        data.password,
        request.state.user_id
    )
    await release_pg_connection(conn)
    return {"change_pw": change_pw, "error_at_html_user": error_at_html_user}


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
