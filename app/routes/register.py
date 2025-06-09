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



class RegisterUserRequest(BaseModel):
    username: str
    name: str
    tel: str
    mail: str
    fediverse_id: str
    password: str
    verify_mail: bool
    verify_fediverse: bool



@router.post("/register/")
async def register_user(data: RegisterUserRequest):
    conn = await get_pg_connection() 
    verification = manager.get_setting("mandatory_user_verification")
    try:
        if verification:

            activation_token = token_generate()
            await conn.execute('''
                INSERT INTO users (username, username_html, name, tel, mail, fediverse_id, password, token, is_activated, activation_token) 
                VALUES ($1,'<b>' || $1::varchar || '</b>',$2,$3,$4,$5,$6,'', false, $7)
            ''', data.username, data.name, data.tel, data.mail, data.fediverse_id, calc_hmac(data.password), activation_token
            )

            if data.verify_mail:
                mail_body = "Hello " + data.name + "\n\n"
                mail_body += "Welcome to the chat.\n"
                mail_body += "To activate your account, please click the link below or paste it into your browser:\n\n"
                mail_body += os.getenv('PROTOCOL') + "://" + os.getenv("DOMAIN_NAME") + "/activate/" + activation_token + "/\n\n"
                mail_body += "Kind regards"
                send_mail(data.mail, "Activate your account", mail_body)

            if data.verify_fediverse:
                text = "Hi, Activation Link: "
                text += os.getenv("DOMAIN_NAME") + "/activate/" + activation_token + "/"
                send_fediverse(data.fediverse_id, text)

        else:
            await conn.execute('''
                INSERT INTO users (username, username_html, name, tel, mail, fediverse_id, password, token) 
                VALUES ($1,'<b>' || $1::varchar || '</b>',$2,$3,$4,$5,$6,'')
            ''', data.username, data.name, data.tel, data.mail, data.fediverse_id, calc_hmac(data.password)
            )


    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await release_pg_connection(conn)
    return {"succecss": True }


# also check admin activate account method in admin/admin
@router.post("/activate_account/")
async def activate_account(activation_token : str):
    conn = await get_pg_connection() 

    query = '''
        UPDATE users
        SET is_activated = true, activation_token = NULL
        WHERE activation_token = $1;
    '''
    try:
        await conn.execute(query, activation_token)
    except:
        pass
    finally:
        await release_pg_connection(conn)
    return True



@router.get("/public_infos/")
async def login_page_info():

    online_list = []
    channels = []
    try:
        # todo visible
        # todo channels
        conn = await get_pg_connection() 
        data = await conn.fetch("SELECT username FROM users WHERE token != ''")
        online_list = [record['username'] for record in data]
        data = await conn.fetch("SELECT name FROM channels WHERE visible = true")
        channels = [record['name'] for record in data]
    except Exception as e:
        print(str(e),flush=True)
    finally:
        if conn:
            await release_pg_connection(conn)


    return {"online_names": online_list, 
            "allow_guest_login": manager.get_setting("allow_guest_login"), 
            "user_verification_mail": manager.get_setting("user_verification_mail"), 
            "user_verification_fediverse": manager.get_setting("user_verification_fediverse"), 
            "display_online": True, 
            "num_users": len(online_list), 
            "show_rooms": True, 
            "channels": channels
            }

