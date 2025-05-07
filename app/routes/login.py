from typing import Annotated
from fastapi import FastAPI, UploadFile, File, HTTPException,APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate, send_mail
from helper import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os

router = APIRouter()





@router.post("/")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    username = form_data.username
    password = form_data.password
    valid = False
    token = token_generate()
    # todo hashing
    
    try:
        conn = await get_pg_connection()
        query = '''
            SELECT password, admin 
            FROM users 
            WHERE LOWER(username) = LOWER($1)
        '''
        result = await conn.fetchrow(query, username)

        if result and result['password'] == password:
            valid = True
            query = '''
                UPDATE users 
                SET token = $1,
                last_login = NOW(),
                last_posted = NOW()
                WHERE username = $2
            '''
            await conn.execute(query, token, username)
    except:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    finally:
        if conn:
            await release_pg_connection(conn)


    if not valid:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    #send_mail("johannes.w@gmx.at", "Test Mail", "Hallo\nEs scheint zu funktionieren." + username)
    return {"access_token": token, "admin": result['admin'], "token_type": "bearer"}


@router.get("/from_token/{token}/")
async def get_user(token: str):

    conn = await get_pg_connection() 
    query = "SELECT username, admin FROM users WHERE token = $1"
    result = await conn.fetchrow(query, token)
    await release_pg_connection(conn)
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return result



@router.get("/logout_token/{token}/")
async def logout_token(token : str):
    
    conn = await get_pg_connection() 
    query = "UPDATE users SET token = '' WHERE token = $1"
    await conn.execute(query, token)
    await release_pg_connection(conn)
    
    return True





@router.post("/lost_password/")
async def lost_password(username : str, mail : str):
    
    conn = await get_pg_connection() 
    query = "SELECT id,mail FROM users WHERE username = $1 AND LOWER(mail) = LOWER($2)"

    result = await conn.fetchrow(query, username, mail)
    
    if result:
        lost_pass_token = token_generate()
        query = '''
            UPDATE users 
            SET lost_password_token = $1,
            lost_password_token_valid_from = NOW()
            WHERE username = $2
        '''
        await conn.execute(query, lost_pass_token, username)
        mail_body = "Hello " + username + "\n\n"
        mail_body += "We received a request to reset the password for your account.\n"
        mail_body += "To set a new password, please click the link below or paste it into your browser:\n\n"
        mail_body += os.getenv('PROTOCOL') + "://" + os.getenv("DOMAIN_NAME") + "/recovery/" + lost_pass_token + "/\n\n"
        mail_body += "Kind regards"
        send_mail(mail, "Lost Password", mail_body)

    await release_pg_connection(conn)
    return True







@router.post("/recover_password/")
async def lost_password(lost_pass_token : str, new_password : str):
    if new_password == "" or lost_pass_token == "": 
        return True
    
    conn = await get_pg_connection() 

    query = '''
        UPDATE users
        SET password = $1, lost_password_token = NULL, lost_password_token_valid_from = NULL
        WHERE lost_password_token = $2
        AND EXTRACT(EPOCH FROM (NOW() - lost_password_token_valid_from)) <= 600;
    '''
    try:
        await conn.execute(query, new_password, lost_pass_token)
    except:
        pass
    finally:
        await release_pg_connection(conn)
    return True







@router.get("/login_page/")
async def login_page_info():
    return {"online_names": ["Chatter 1", "Chatter 2", "Chatter 3"], "guest_login": True, "display_online": True, "number_online": 3, "show_rooms": True, "rooms": ["Hauptchat", "Nebenchat"]}