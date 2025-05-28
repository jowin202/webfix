from fastapi import APIRouter
from io import BytesIO
from helper import token_generate
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from typing import Dict, Any, List
from settings import SettingsManager

from db import pg_db_init, pg_db_remove, get_pg_connection, release_pg_connection

router = APIRouter()



manager = SettingsManager()




# also check activate account method in login
@router.post("/admin_activate_account/")
async def admin_activate_account(username : str):
    conn = await get_pg_connection() 
    status = True
    query = '''
        UPDATE users
        SET is_activated = true, activation_token = NULL
        WHERE username = $1;
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

