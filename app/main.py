import asyncio
import asyncpg
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocketDisconnect, Depends

from fastapi.templating import Jinja2Templates

from routes.login import logout_token

import os 
import json

from contextlib import asynccontextmanager
from datetime import datetime

from helper import get_pg_connection, initialize_connection_pool, release_pg_connection, verify_token, verify_token_admin
from dbinit import pg_db_init

from settings import SettingsManager


CHANNEL = "mynotifications"


# Database config
DB_CONFIG = {
    "user": os.getenv('POSTGRES_USER'),
    "password": os.getenv('POSTGRES_PASSWORD'),
    "database": os.getenv('POSTGRES_DB'),
    "host": os.getenv('POSTGRES_HOST', 'localhost'),
    "port": os.getenv('POSTGRES_PORT', 5432) 
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_connection_pool()
    await pg_db_init()

    manager = SettingsManager()
    await manager.initialize()

    await manager.set_setting_if_not_exists("allow_guest_login", True)
    await manager.set_setting_if_not_exists("activate_timeout", True)
    await manager.set_setting_if_not_exists("mandatory_user_verification", True)

    await manager.set_setting_if_not_exists("timeout_time", 180)
    await manager.set_setting_if_not_exists("pw_recovery_token_valid_time", 600)
    
    await manager.set_setting_if_not_exists("announcement_general", "Welcome to our chat, $USER! ")
    await manager.set_setting_if_not_exists("announcement_guests", "Hello $USER, Please register your username!")
    await manager.set_setting_if_not_exists("announcement_registered_users", "Welcome and thanks for registering, $USER!")
    await manager.set_setting_if_not_exists("announcement_team", "Who is online at 9pm?")
    

    asyncio.create_task(timeout_check())

    yield # this is mandatory

app = FastAPI(title="Webfix API", lifespan=lifespan)

async def timeout_check():
    refresh_intervall = 10
    manager = SettingsManager()
    while True:
        conn = await get_pg_connection()
        
        result = await conn.fetch("""SELECT id, username, token, NOW()-last_posted AS diff FROM users WHERE last_posted IS NOT NULL AND last_posted < NOW() - ($1 || ' seconds')::interval AND token != '' """, str(manager.get_setting("timeout_time")))
        for row in result:
            msg = '{"cat": "statusmsg", "msg": "Timeout"}'
            await conn.execute(f"NOTIFY whisper_{row['id']}, '{msg}' ")
            await logout_token(row['token']) # from endpoint 
            

        row = await conn.fetchrow("""
            SELECT MIN((last_posted + ($1 || ' seconds')::interval) - NOW()) AS remaining
            FROM users
            WHERE token != ''
            AND last_posted IS NOT NULL
            AND last_posted + ($1 || ' seconds')::interval > NOW()
                                           """, str(manager.get_setting("timeout_time")))
        
        if row and row['remaining']:
            refresh_intervall = int(row['remaining'].total_seconds())+5 # 5 sec tolerance for testing
        else:
            refresh_intervall = int(manager.get_setting("timeout_time")/2)  # or 0 or some fallback

        # print(refresh_intervall, flush=True)
        await release_pg_connection(conn)
        await asyncio.sleep(refresh_intervall)




@app.websocket("/ws2")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")

    valid = False
    message = ""
    username = ""
    id = -1
    is_guest = False
    try:
        conn = await get_pg_connection()
        query = '''
            SELECT id, username,remove_on_logout
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
        

        x_forwarded_for = websocket.headers.get("x-forwarded-for")
        client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else websocket.client.host
        ip_check_query = "SELECT 1 FROM banned_ips WHERE ip = $1"
        ip_blocked = await conn.fetchval(ip_check_query, client_ip)

        if ip_blocked:
            valid = False
            message = "IP blocked"


        if valid:
            await conn.execute(f"NOTIFY whisper_{id}, '{json.dumps({'cat': 'statusmsg', 'msg': 'double login'})}'")
            await conn.execute(f"NOTIFY whisper_{id}, 'exit'")
    except Exception as e:
        print("exception: " + str(e), flush=True)
        await websocket.close() # this only happen if error
        return # quit here
    finally:
        await release_pg_connection(conn)

    await websocket.accept()
    await websocket.send_text(f'{{"cat": "statusmsg", "msg": "stream opened for {username}, id: {id}"}}')

    if not valid:
        await websocket.send_text(f'{{"cat": "statusmsg", "msg": "{message}"}}')
        await websocket.close()
        return


    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.add_listener(CHANNEL, lambda *args: asyncio.create_task(notify_ws(args, websocket)))
    await conn.add_listener("whisper_" + str(id), lambda *args: asyncio.create_task(notify_ws_w(args, websocket)))


    try:
        manager = SettingsManager()
        announcement =  manager.get_setting("announcement_general").replace("$USER", username)
        announcement_guests =  manager.get_setting("announcement_guests").replace("$USER", username)
        announcement_registered =  manager.get_setting("announcement_registered_users").replace("$USER", username)

        if announcement and announcement != "":
            await websocket.send_text(f'{{"cat": "announcement", "msg": "{announcement}"}}')

        if is_guest and announcement_guests and announcement_guests != "":
            await websocket.send_text(f'{{"cat": "announcement", "msg": "{announcement_guests}"}}')
        elif announcement_registered and announcement_registered != "":
            await websocket.send_text(f'{{"cat": "announcement", "msg": "{announcement_registered}"}}')
            
        while True:
            # Wait for any message or ping to keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("WebSocket error:", e)
    finally:
        print("Cleaning up...",flush=True)
        await conn.remove_listener(CHANNEL, notify_ws)
        await conn.close()


async def notify_ws(args, websocket: WebSocket):
    _, pid, channel, payload = args
    try:
        await websocket.send_text(payload)
    except:
        pass

async def notify_ws_w(args, websocket: WebSocket):
    _, pid, channel, payload = args
    if payload == 'exit':
        try:
            await websocket.send_text('{"cat": "statusmsg", "msg": "stream closed"}')
        except:
            pass
        await websocket.close()
    else:
        await websocket.send_text(payload)



from routes import input
from routes import login
from routes import register
from routes import pwmanage
from routes import toplist
from routes.admin import settings
from routes.admin import admin


app.include_router(input.router, tags=["input"], prefix="/api/input", dependencies=[Depends(verify_token)])
app.include_router(login.router, tags=["login"], prefix="/api/login")
app.include_router(register.router, tags=["register"], prefix="/api/register")
app.include_router(pwmanage.router, tags=["pwmanage"], prefix="/api/pwmanage")
app.include_router(toplist.router, tags=["toplist"], prefix="/api/toplist")


app.include_router(settings.router, tags=["settings"], prefix="/api/settings", dependencies=[Depends(verify_token_admin)])
app.include_router(admin.router, tags=["admin"], prefix="/api/admin", dependencies=[Depends(verify_token_admin)])


@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/index.html", "r") as f:
        return f.read() 

app.mount("/", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")

@app.get("/test/{token}/", response_class=HTMLResponse)
async def test_minimal_frontend(request: Request, token : str):
    return templates.TemplateResponse("client.html", {"request": request, "token": token})