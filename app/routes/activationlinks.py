from fastapi import APIRouter
from io import BytesIO
from helper import token_generate
from db import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from typing import Dict, Any, List
from settings import SettingsManager


router = APIRouter()






# also check activate account method in login
@router.get("/activate/{activation_token}/")
async def activate_account(activation_token : str):
    if len(activation_token) < 4:
        return "Link invalid"
    conn = await get_pg_connection() 
    status = True
    query = '''
        UPDATE users
        SET is_activated = true, activation_token = NULL
        WHERE activation_token = $1;
    '''
    try:
        await conn.execute(query, activation_token)
    except:
        status = False
    finally:
        await release_pg_connection(conn)
    
    if status:
        return "User was activated successfully."
    return "Link invalid"



