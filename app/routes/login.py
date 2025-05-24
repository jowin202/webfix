from typing import Annotated
from fastapi import FastAPI, UploadFile, File, HTTPException,APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate, send_mail, send_fediverse, calc_hmac, verify_token
from helper import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
import json

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
            SELECT id, password, is_activated, admin, channel_id 
            FROM users 
            WHERE LOWER(username) = LOWER($1)
        '''
        result = await conn.fetchrow(query, username)
        user_id = result['id']

        if not manager.get_setting("mandatory_user_verification") or result['is_activated']:
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
                
                # logout if logged in
                await conn.execute(f"NOTIFY whisper_{user_id}, '{json.dumps({'cat': 'statusmsg', 'msg': 'double login'})}'")
                await conn.execute(f"NOTIFY whisper_{user_id}, 'exit'")
    except:
        valid = False
    finally:
        if conn:
            await release_pg_connection(conn)

    if not valid:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    return {"access_token": token, "admin": result['admin'], "channel_id": result['channel_id'], "token_type": "bearer"}





@router.post("/guest_login/")
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

        if not manager.get_setting("allow_guest_login"):
            valid = False
        

        # create temp user
        if valid:
            await conn.execute('''
                INSERT INTO users (username, username_html, token, password,  created, last_posted, is_activated, remove_on_logout) 
                VALUES ($1, '<b>' || $1::varchar || '</b>', $2, '', NOW(), NOW(), true, true)
                ON CONFLICT (username) DO NOTHING
            ''', username, token)


    except:
        valid = False
    finally:
        if conn:
            await release_pg_connection(conn)

    if not valid:
        raise HTTPException(status_code=400, detail="Guest Login Error")
    # TODO default guest channel
    return {"access_token": token, "channel_id": 1, "token_type": "bearer"}




# this is also for timeout, no addition to online time
@router.get("/from_token/{token}/")
async def login_token(token : str):
    
    conn = await get_pg_connection() 
    query = '''
        SELECT id, username, admin, channel_id
        FROM users
        WHERE token = $1
    '''
    row = await conn.fetchrow(query, token)

    # no double login check because stream is doing it 
    await release_pg_connection(conn)

    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    
    username = row['username'] if row and "username" in row else ""
    admin = row['admin'] if row and "admin" in row else ""
    channel_id = row['channel_id'] if row and "channel_id" in row else 1
    return { "username" : username, "admin": admin, "channel_id": row['channel_id']}



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



