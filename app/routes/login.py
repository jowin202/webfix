from typing import Annotated
from fastapi import FastAPI, UploadFile, File, HTTPException,APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate, send_mail, send_fediverse, calc_hmac, verify_token
from helper import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os

from settings import SettingsManager

router = APIRouter()


manager = SettingsManager()




@router.post("/")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    username = form_data.username
    password = calc_hmac(form_data.password)
    valid = False
    token = token_generate()
    
    try:
        conn = await get_pg_connection()
        query = '''
            SELECT password, is_activated, admin 
            FROM users 
            WHERE LOWER(username) = LOWER($1)
        '''
        result = await conn.fetchrow(query, username)


        if not await manager.get_setting("mandatory_user_verification") or result['is_activated']:
            if result and result['password'] == password:
                valid = True
                query = '''
                    UPDATE users 
                    SET token = $1,
                    last_login = NOW(),
                    last_posted = NOW(),
                    login_count = login_count+1
                    WHERE LOWER(username) = LOWER($2)
                '''
                await conn.execute(query, token, username)
        
    except:
        valid = False
    finally:
        if conn:
            await release_pg_connection(conn)


    if not valid:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    return {"access_token": token, "admin": result['admin'], "token_type": "bearer"}





@router.post("/guest_login")
async def login(username : str):
    valid = True
    token = token_generate()
    
    try:
        # check if user exists
        conn = await get_pg_connection()
        query = '''
            SELECT 1
            FROM users 
            WHERE LOWER(username) = LOWER($1)
        '''
        result = await conn.fetchrow(query, username)

        # check if user exists
        if result is not None:
            valid = False

        if not await manager.get_setting("allow_guest_login"):
            valid = False
        

        # create temp user
        if valid:
            await conn.execute('''
                INSERT INTO users (username, token, password,  created, last_posted, is_activated, remove_on_logout) 
                VALUES ($1, $2, '', NOW(), NOW(), true, true)
                ON CONFLICT (username) DO NOTHING
            ''', username, token)


    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        valid = False
    finally:
        if conn:
            await release_pg_connection(conn)

    if not valid:
        raise HTTPException(status_code=400, detail="Guest Login Error")
    return {"access_token": token, "token_type": "bearer"}






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
    query = '''
        UPDATE users 
        SET token = '',
        last_posted = NULL
        WHERE token = $1
        RETURNING id
    '''
    user_id = await conn.fetchval(query, token)
    await conn.execute(f"NOTIFY whisper_{user_id}, 'exit'")

    # cleanup guests
    query = '''
        DELETE FROM users
        WHERE remove_on_logout = true
        AND token = '';
    '''
    await conn.execute(query)
    
    await release_pg_connection(conn)
    
    return True


@router.get("/logout/")
async def logout(token: str = Depends(verify_token)):
    
    conn = await get_pg_connection() 
    query = '''
        UPDATE users 
        SET token = '',
        last_posted = NULL
        WHERE token = $1
        RETURNING id
    '''
    user_id = await conn.fetchval(query, token)
    await conn.execute(f"NOTIFY whisper_{user_id}, 'exit'")

    # cleanup guests
    query = '''
        DELETE FROM users
        WHERE remove_on_logout = true
        AND token = '';
    '''
    await conn.execute(query)
    await release_pg_connection(conn)
    
    return True







@router.post("/register/")
async def register_user(username : str, name : str, tel : str, mail : str, fediverse_id : str, password : str, verify_mail : bool, verify_fediverse : bool):

    conn = await get_pg_connection() 
    verification = await manager.get_setting("mandatory_user_verification")


    try:
        if verification:

            activation_token = token_generate()
            await conn.execute('''
                INSERT INTO users (username, name, tel, mail, fediverse_id, password, token, is_activated, activation_token) 
                VALUES ($1,$2,$3,$4,$5,$6,'', false, $7)
            ''', username, name, tel, mail, fediverse_id, calc_hmac(password), activation_token
            )

            if verify_mail:
                mail_body = "Hello " + name + "\n\n"
                mail_body += "Welcome to the chat.\n"
                mail_body += "To activate your account, please click the link below or paste it into your browser:\n\n"
                mail_body += os.getenv('PROTOCOL') + "://" + os.getenv("DOMAIN_NAME") + "/activate/" + activation_token + "/\n\n"
                mail_body += "Kind regards"
                send_mail(mail, "Activate your account", mail_body)

            if verify_fediverse:
                text = "Hi, Activation Link: "
                text += os.getenv("DOMAIN_NAME") + "/activate/" + activation_token + "/"
                send_fediverse(fediverse_id, text)

        else:
            await conn.execute('''
                INSERT INTO users (username, name, tel, mail, fediverse_id, password, token) 
                VALUES ($1,$2,$3,$4,$5,$6,'')
            ''', username, name, tel, mail, fediverse_id, calc_hmac(password)
            )


    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await release_pg_connection(conn)
    return True




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



@router.get("/login_page/")
async def login_page_info():

    online_list = []
    try:
        # todo visible
        # todo channels
        conn = await get_pg_connection() 
        data = await conn.fetch("SELECT username FROM users WHERE token != ''")
        online_list = [record['username'] for record in data]
    except:
        pass
    finally:
        if conn:
            await release_pg_connection(conn)


    return {"online_names": online_list, 
            "allow_guest_login": await manager.get_setting("allow_guest_login"), 
            "display_online": True, 
            "number_online": len(online_list), 
            "show_rooms": True, 
            "rooms": ["Hauptchat", "Nebenchat"]
            }



