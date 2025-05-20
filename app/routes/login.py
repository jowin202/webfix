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



    # logout if logged in
    await conn.execute(f"NOTIFY whisper_{user_id}, 'exit'")

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


# this is also for timeout, no addition to online time
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

    # cleanup guests
    query = '''
        DELETE FROM users
        WHERE remove_on_logout = true
        AND token = '';
    '''
    await conn.execute(query)

    # first logout, then close stream
    await conn.execute(f"NOTIFY whisper_{user_id}, 'exit'")
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



