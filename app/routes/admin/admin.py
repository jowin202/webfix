from fastapi import APIRouter
from io import BytesIO
from helper import token_generate
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from typing import Dict, Any, List
from settings import SettingsManager
from pydantic import BaseModel

from db import pg_db_init, pg_db_remove, get_pg_connection, release_pg_connection

router = APIRouter()



manager = SettingsManager()



class MuteUserRequest(BaseModel):
    username: str
    time: int

class KickUserRequest(BaseModel):
    username: str
    time: int


# also check activate account method in login
@router.post("/admin_activate_account/")
async def admin_activate_account(username : str):
    conn = await get_pg_connection() 
    status = True
    query = '''
        UPDATE users
        SET is_activated = true, activation_token = NULL
        WHERE LOWER(username) = LOWER($1);
    '''
    try:
        await conn.execute(query, username)
    except:
        status = False
    finally:
        await release_pg_connection(conn)
    return status




@router.post("/reset_database/")
async def reset_database():
    await pg_db_remove()
    await pg_db_init()
    return True



#todo: change to ID
@router.post("/kick_user/")
async def kick_user(data: KickUserRequest):
    conn = await get_pg_connection() 
    status = True
    try:
        if data.time > 0:
            query = '''
                UPDATE users
                SET kicked_until = NOW() + (INTERVAL '1 second' * $2)
                WHERE username = $1;
                '''
            await conn.execute(query, data.username, data.time)
        elif data.time < 0:
            query = '''
                UPDATE users
                SET kicked_until = 'infinity'
                WHERE LOWER(username) = LOWER($1);
                '''
            await conn.execute(query, data.username)
        elif data.time == 0:
            query = '''
                UPDATE users
                SET kicked_until = '-infinity'
                WHERE LOWER(username) = LOWER($1);
                '''
            await conn.execute(query, username)


        # TODO: close stream
    except:
        status = False
    finally:
        await release_pg_connection(conn)
    return status


#todo: change to ID
@router.post("/mute_user/")
async def mute_user(data : MuteUserRequest):
    conn = await get_pg_connection() 
    status = True

    try:
        if data.time > 0:
            query = '''
                UPDATE users
                SET muted_until = NOW() + (INTERVAL '1 second' * $2)
                WHERE LOWER(username) = LOWER($1);
                '''
            await conn.execute(query, data.username, data.time)
        elif data.time < 0:
            query = '''
                UPDATE users
                SET muted_until = 'infinity'
                WHERE LOWER(username) = LOWER($1);
                '''
            await conn.execute(query, data.username)
        elif data.time == 0:
            query = '''
                UPDATE users
                SET muted_until = '-infinity'
                WHERE LOWER(username) = LOWER($1);
                '''
            await conn.execute(query, data.username)
    except Exception as e:
        status = False
    finally:
        await release_pg_connection(conn)
    return status


@router.delete("/delete_id/{user_id}/")
async def delete_user(user_id: int):
    conn = await get_pg_connection()
    status = True

    #TODO: close stream

    try:
        query = '''
            DELETE FROM users
            WHERE id = $1;
        '''
        await conn.execute(query, user_id)
    except Exception as e:
        status = False
    finally:
        await release_pg_connection(conn)
    return status


