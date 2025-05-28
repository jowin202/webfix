from typing import Annotated
from fastapi import FastAPI, UploadFile, File, HTTPException,APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate, send_mail, send_fediverse, calc_hmac
from db import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os

from settings import SettingsManager

router = APIRouter()


manager = SettingsManager()



class LostPasswordMailRequest(BaseModel):
    username: str
    mail: str

class LostPasswordFediverseRequest(BaseModel):
    username: str
    fediverse_id: str

class newPasswordRequest(BaseModel):
    lost_pass_token: str
    new_pass: str




@router.post("/lost_password_mail/")
async def lost_password_mail(data : LostPasswordMailRequest):
    
    conn = await get_pg_connection() 
    query = "SELECT id,mail FROM users WHERE LOWER(username) = LOWER($1) AND LOWER(mail) = LOWER($2)"

    result = await conn.fetchrow(query, data.username, data.mail)
    
    if result:
        lost_pass_token = token_generate()
        query = '''
            UPDATE users 
            SET lost_password_token = $1,
            lost_password_token_valid_from = NOW()
            WHERE LOWER(username) = LOWER($2)
        '''
        await conn.execute(query, lost_pass_token, data.username)
        mail_body = "Hello " + data.username + "\n\n"
        mail_body += "We received a request to reset the password for your account.\n"
        mail_body += "To set a new password, please click the link below or paste it into your browser:\n\n"
        mail_body += os.getenv('PROTOCOL') + "://" + os.getenv("DOMAIN_NAME") + "/recovery/" + lost_pass_token + "/\n\n"
        mail_body += "Kind regards"
        send_mail(data.mail, "Lost Password", mail_body)

    await release_pg_connection(conn)
    return True





@router.post("/lost_password_fediverse/")
async def lost_password_fediverse(data: LostPasswordFediverseRequest):
    
    conn = await get_pg_connection() 
    query = "SELECT id,fediverse_id FROM users WHERE username = $1 AND LOWER(fediverse_id) = LOWER($2)"

    result = await conn.fetchrow(query, data.username, data.fediverse_id)
    
    if result:
        lost_pass_token = token_generate()
        query = '''
            UPDATE users 
            SET lost_password_token = $1,
            lost_password_token_valid_from = NOW()
            WHERE LOWER(username) = LOWER($2)
        '''
        await conn.execute(query, lost_pass_token, data.username)
        text = "Hi, Password Recovery Link: "
        text += os.getenv("DOMAIN_NAME") + "/recovery/" + lost_pass_token + "/"
        send_fediverse(data.fediverse_id, text)

    await release_pg_connection(conn)
    return True




@router.post("/recover_password/")
async def recover_password(data: newPasswordRequest): 
    if data.new_pass == "" or data.lost_pass_token == "": 
        return True
    
    conn = await get_pg_connection() 

    query = '''
        UPDATE users
        SET password = $1, lost_password_token = NULL, lost_password_token_valid_from = NULL
        WHERE lost_password_token = $2
        AND EXTRACT(EPOCH FROM (NOW() - lost_password_token_valid_from)) <= $3;
    '''
    try:
        await conn.execute(query, calc_hmac(data.new_pass), data.lost_pass_token, manager.get_setting("pw_recovery_token_valid_time"))
    except:
        pass
    finally:
        await release_pg_connection(conn)
    return True
