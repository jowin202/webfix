from fastapi import APIRouter
from io import BytesIO
from helper import token_generate
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from typing import Dict, Any, List
from settings import SettingsManager
from pydantic import BaseModel

from db import pg_db_init, pg_db_remove, get_pg_connection, release_pg_connection

import json

router = APIRouter()



manager = SettingsManager()



class MuteUserRequest(BaseModel):
    silent: bool
    user_id: int
    time: int

class KickUserRequest(BaseModel):
    silent: bool
    user_id: int
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
                SET kicked_until = NOW() + (INTERVAL '1 second' * $2),
                token = '',
                last_posted = NULL
                WHERE id = $1;
                '''
            await conn.execute(query, data.user_id, data.time)
        elif data.time < 0:
            query = '''
                UPDATE users
                SET kicked_until = 'infinity',
                token = '',
                last_posted = NULL
                WHERE id = $1;
                '''
            await conn.execute(query, data.user_id)
        elif data.time == 0:
            query = '''
                UPDATE users
                SET kicked_until = '-infinity'
                WHERE id = $1;
                '''
            await conn.execute(query, data.user_id)


        # notify only for kicking
        if data.time != 0:
            query = '''
                SELECT username, channel_id
                FROM users
                WHERE id = $1;
                '''
            result = await conn.fetchrow(query, data.user_id)
            username = result['username']
            channel_id = result['channel_id']
            
            #close stream
            if not data.silent:
                await conn.execute(f"NOTIFY channel_{channel_id}, '{json.dumps({'cat': 'statusmsg', 'username': 'ChatBot', 'msg': username + ' wurde gekickt.'})}'")
            await conn.execute(f"NOTIFY whisper_{data.user_id}, 'exit'")



    except Exception as e:
        print(e, flush=True)
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
                WHERE id = $1;
                '''
            await conn.execute(query, data.user_id, data.time)
        elif data.time < 0:
            query = '''
                UPDATE users
                SET muted_until = 'infinity'
                WHERE id = $1;
                '''
            await conn.execute(query, data.user_id)
        elif data.time == 0:
            query = '''
                UPDATE users
                SET muted_until = '-infinity'
                WHERE id = $1;
                '''
            await conn.execute(query, data.user_id)


        
        # notify only muting 
        if data.time != 0:
            query = '''
                SELECT username, channel_id
                FROM users
                WHERE id = $1;
                '''
            result = await conn.fetchrow(query, data.user_id)
            username = result['username']
            channel_id = result['channel_id']
            
            #close stream
            if not data.silent:
                time = data.time if data.time > 0 else 'infinite'
                await conn.execute(f"NOTIFY channel_{channel_id}, '{json.dumps({'cat': 'statusmsg', 'username': 'ChatBot', 'msg': username + ' was muted for ' + str(time) + ' seconds.'})}'")


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


