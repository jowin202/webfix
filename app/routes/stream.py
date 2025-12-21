from typing import Annotated
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException,APIRouter, Depends, Request
from helper import token_generate, send_mail, send_fediverse, calc_hmac
from db import get_pg_connection, release_pg_connection
import os
import json
import asyncpg

from settings import SettingsManager

router = APIRouter()



# Database config
DB_CONFIG = {
    "user": os.getenv('POSTGRES_USER'),
    "password": os.getenv('POSTGRES_PASSWORD'),
    "database": os.getenv('POSTGRES_DB'),
    "host": os.getenv('POSTGRES_HOST', 'localhost'),
    "port": os.getenv('POSTGRES_PORT', 5432) 
}


@router.websocket("/ws2")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")

    valid = False
    message = ""
    username = ""
    id = -1
    channel_id = 1
    is_guest = False
    try:
        conn = await get_pg_connection()
        query = '''
            SELECT id, username, channel_id, remove_on_logout
            FROM users 
            WHERE token = $1 
        '''
        result = await conn.fetchrow(query, token) 
        if result:
            valid = True
            username = result['username']
            id = int(result['id'])
            channel_id = int(result['channel_id'])
            is_guest = True if result['remove_on_logout'] else False
        else:
            message = "Unknown token"
        

        x_forwarded_for = websocket.headers.get("x-forwarded-for")
        client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else websocket.client.host
        ip_check_query = "SELECT 1 FROM banned_ips WHERE ip = $1"
        ip_blocked = await conn.fetchval(ip_check_query, client_ip)

        if ip_blocked:
            valid = False
            message = "IP blocked"


        if valid:
            await conn.execute(f"NOTIFY whisper_{id}, '{json.dumps({'cat': 'statusmsg', 'msg': 'double login detected'})}'")
            await conn.execute(f"NOTIFY whisper_{id}, 'exit'")
    except Exception as e:
        print("exception: " + str(e), flush=True)
        await websocket.close() # this only happen if error
        return # quit here
    finally:
        if (conn):
            await release_pg_connection(conn)

    await websocket.accept()
    #await websocket.send_text(f'{{"cat": "statusmsg", "msg": "stream opened for {username}, id: {id}"}}')

    if not valid:
        await websocket.send_text(f'{{"cat": "statusmsg", "msg": "{message}"}}')
        await websocket.close()
        return

    async def switch_channel(new_channel_id):
        nonlocal current_listener, channel_id
        #print(f"Switching from {channel_id} to {new_channel_id}", flush=True)
        
        payload1 = json.dumps({"cat": "userleft", "username": username})
        payload2 = json.dumps({"cat": "userenters", "username": username})

        await conn.execute(f"NOTIFY channel_{str(channel_id)}, '{payload1}'")
        await conn.remove_listener("channel_" + str(channel_id), current_listener)
        channel_id = new_channel_id
        await conn.add_listener("channel_" + str(channel_id), current_listener)
        await conn.execute(f"NOTIFY channel_{str(channel_id)}, '{payload2}'")
    
    def create_listener(websocket):
        async def listener(*args):
            await notify_ws(args, websocket)
        return listener

    def create_wh_listener(websocket, switch_channel_callback):
        async def listener(*args):
            await notify_ws_wh(args, websocket,switch_channel_callback)
        return listener

    global_listener = create_listener(websocket)
    current_listener = create_listener(websocket)
    whisper_listener = create_wh_listener(websocket,switch_channel)


    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.add_listener("global", global_listener)
    await conn.add_listener("channel_" + str(channel_id), current_listener)
    await conn.add_listener("whisper_" + str(id), whisper_listener)

    try:
        manager = SettingsManager()
        announcement =  manager.get_setting("announcement_general").replace("$USER", username)
        announcement_guests =  manager.get_setting("announcement_guests").replace("$USER", username)
        announcement_registered =  manager.get_setting("announcement_registered_users").replace("$USER", username)

        if announcement:
            await websocket.send_text(json.dumps({"cat": "announcement", "msg": announcement}))

        if is_guest and announcement_guests:
            await websocket.send_text(json.dumps({"cat": "announcement", "msg": announcement_guests}))
        elif announcement_registered:
            await websocket.send_text(json.dumps({"cat": "announcement", "msg": announcement_registered}))
            
        while True:
            # Wait for any message or ping to keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("WebSocket error:", e)
    finally:
        print("Cleaning up...",flush=True)
        await conn.remove_listener("global", global_listener)
        await conn.remove_listener("channel_" + str(channel_id), current_listener)
        await conn.remove_listener("whisper_" + str(id), whisper_listener)
        await conn.close()


async def notify_ws(args, websocket: WebSocket):
    _, pid, channel, payload = args
    try:
        await websocket.send_text(payload)
    except:
        pass

async def notify_ws_wh(args, websocket: WebSocket, switch_channel_callback):
    _, pid, channel, payload = args
    if payload == 'exit':
        try:
            await websocket.send_text('{"cat": "statusmsg", "msg": "stream closed"}')
        except:
            pass
        await websocket.close()
    elif payload.startswith("goto"):
        await switch_channel_callback(int(payload.split()[1]))
    else:
        await websocket.send_text(payload)

