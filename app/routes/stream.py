from fastapi import WebSocket, WebSocketDisconnect, APIRouter
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






@router.websocket("/ws3")
async def websocket_endpoint_multi_channel(websocket: WebSocket):
    token = websocket.query_params.get("token")

    valid = False
    message = ""
    username = ""
    id = -1
    channel_ids = []
    is_guest = False
    conn = None
    try:
        conn = await get_pg_connection()

        # basic infos
        query = '''
            SELECT id, username, remove_on_logout
            FROM users 
            WHERE token = $1 
        '''
        result = await conn.fetchrow(query, token) 
        if result:
            valid = True
            username = result['username']
            id = int(result['id'])
            is_guest = True if result['remove_on_logout'] else False
        else:
            message = "Unknown token"
        

        # public channels
        query = '''
                SELECT id
                FROM channels 
                WHERE always_available = true 
            UNION
                SELECT channel_id
                FROM channel_members
                WHERE user_id = $1
        '''
        result = await conn.fetch(query, id)
        if result:
            channel_ids = [int(row['id']) for row in result]



        x_forwarded_for = websocket.headers.get("x-forwarded-for")
        client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else websocket.client.host
        ip_check_query = "SELECT 1 FROM banned_ips WHERE ip = $1"
        ip_blocked = await conn.fetchval(ip_check_query, client_ip)

        if ip_blocked:
            valid = False
            message = "IP blocked"


        if valid:
            await conn.execute("SELECT pg_notify($1, $2)", f"whisper_{id}", json.dumps({'cat': 'statusmsg', 'msg': 'double login detected'}))
            await conn.execute("SELECT pg_notify($1, $2)", f"whisper_{id}", "exit")
    except Exception as e:
        print("exception: " + str(e), flush=True)
        await websocket.close()
        return # quit here
    finally:
        if conn is not None:
            await release_pg_connection(conn)

    await websocket.accept()

    if not valid:
        await websocket.send_text(f'{{"cat": "statusmsg", "msg": "{message}"}}')
        await websocket.close()
        return

    listen_conn = await asyncpg.connect(**DB_CONFIG)

    async def add_channel(channel_id):
        nonlocal current_channel_listeners
        if channel_id in current_channel_listeners:
            return

        payload = json.dumps({"cat": "userenters", "username": username, "channel": channel_id})

        listener = create_listener(websocket, add_channel, remove_channel)
        current_channel_listeners[channel_id] = listener

        await listen_conn.add_listener("channel_" + str(channel_id), listener)
        await listen_conn.execute("SELECT pg_notify($1, $2)", "channel_" + str(channel_id), payload)


    async def remove_channel(channel_id):
        nonlocal current_channel_listeners
        listener = current_channel_listeners.get(channel_id)
        if listener is None:
            return

        payload = json.dumps({"cat": "userleft", "username": username, "channel": channel_id})
        await listen_conn.execute("SELECT pg_notify($1, $2)", "channel_" + str(channel_id), payload)
        await listen_conn.remove_listener("channel_" + str(channel_id), listener)
        del current_channel_listeners[channel_id]


    def create_listener(websocket, add_channel_callback, remove_channel_callback):
        async def listener(*args):
            await notify_ws(args, websocket, add_channel_callback, remove_channel_callback)
        return listener

    current_channel_listeners = {}
    global_listener = create_listener(websocket, add_channel, remove_channel)
    whisper_listener = create_listener(websocket, add_channel, remove_channel)


    await listen_conn.add_listener("global", global_listener)
    for channel_id in channel_ids:
        await add_channel(channel_id)
    await listen_conn.add_listener("whisper_" + str(id), whisper_listener)

    try:
        manager = SettingsManager()
        announcement = (manager.get_setting("announcement_general") or "").replace("$USER", username)
        announcement_guests = (manager.get_setting("announcement_guests") or "").replace("$USER", username)
        announcement_registered = (manager.get_setting("announcement_registered_users") or "").replace("$USER", username)

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
        pass
    except Exception as e:
        print("WebSocket error:", e)
    finally:
        for channel_id in list(current_channel_listeners.keys()):
            try:
                await remove_channel(channel_id)
            except Exception:
                pass
        try:
            await listen_conn.remove_listener("global", global_listener)
        except Exception:
            pass
        try:
            await listen_conn.remove_listener("whisper_" + str(id), whisper_listener)
        except Exception:
            pass
        await listen_conn.close()



async def notify_ws(args, websocket: WebSocket, add_channel_callback, remove_channel_callback):
    _, pid, channel, payload = args
    if payload == 'exit':
        try:
            await websocket.send_text('{"cat": "statusmsg", "msg": "stream closed"}')
        except:
            pass
        await websocket.close()
    elif payload.startswith("add "):
        try:
            await add_channel_callback(int(payload.split()[1]))
        except Exception:
            pass
    elif payload.startswith("remove "):
        try:
            await remove_channel_callback(int(payload.split()[1]))
        except Exception:
            pass
    else:
        try:
            await websocket.send_text(payload)
        except Exception:
            pass
