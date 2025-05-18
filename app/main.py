import asyncio
import asyncpg
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocketDisconnect, Depends

from fastapi.templating import Jinja2Templates



import os 

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

    await manager.set_setting_if_not_exists("timeout_time", 60)
    await manager.set_setting_if_not_exists("pw_recovery_token_valid_time", 600)
    
    await manager.set_setting_if_not_exists("announcement_general", "Welcome to our chat!")
    await manager.set_setting_if_not_exists("announcement_guests", "Please register your username!")
    await manager.set_setting_if_not_exists("announcement_registered_users", "Welcome and thanks for registering!")
    await manager.set_setting_if_not_exists("announcement_team", "Who is online at 9pm?")
    

    asyncio.create_task(timeout_check())

    yield # this is mandatory

app = FastAPI(title="Webfix API", lifespan=lifespan)


# deprecated: remove this when channels exist
@app.post("/exit")
async def send_notification():
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute(f"NOTIFY {CHANNEL}, 'exit'")
    await conn.close()
    return {"status": "signal sent" }



async def timeout_check():
    refresh_intervall = 10
    manager = SettingsManager()
    while True:
        conn = await get_pg_connection()
        
        result = await conn.fetch("""SELECT username, token, NOW()-last_posted AS diff FROM users WHERE last_posted IS NOT NULL AND last_posted < NOW() - ($1 || ' seconds')::interval AND token != '' """, str(await manager.get_setting("timeout_time")))
        for row in result:
            pass
            #print(row['username'] +  " " + row['token'] + " " + str(int(row['diff'].total_seconds())))
            # TODO: timeout 


        row = await conn.fetchrow("""
            SELECT MIN((last_posted + ($1 || ' seconds')::interval) - NOW()) AS remaining
            FROM users
            WHERE token != ''
            AND last_posted IS NOT NULL
            AND last_posted + ($1 || ' seconds')::interval > NOW()
                                           """, str(await manager.get_setting("timeout_time")))
        
        if row and row['remaining']:
            refresh_intervall = int(row['remaining'].total_seconds())+5 # 5 sec tolerance for testing
        else:
            refresh_intervall = int(await manager.get_setting("timeout_time")/2)  # or 0 or some fallback

        #print(remaining_seconds, flush=True)
        await release_pg_connection(conn)
        await asyncio.sleep(refresh_intervall)








# WebSocket endpoint that listens for PostgreSQL NOTIFY messages
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text('{"cat": "statusmsg", "msg": "stream opened"}')
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.add_listener(CHANNEL, lambda *args: asyncio.create_task(notify_ws(args, websocket)))


    try:
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



@app.websocket("/ws2")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")

    valid = False
    message = ""
    username = ""
    id = -1
    try:
        conn = await get_pg_connection()
        query = '''
            SELECT id, username
            FROM users 
            WHERE token = $1 
        '''
        result = await conn.fetchrow(query, token)
        #print(result['username'], flush=True)        
        if result:
            valid = True
            username = result['username']
            id = int(result['id'])
        else:
            message = "Unknown token"
        

        x_forwarded_for = websocket.headers.get("x-forwarded-for")
        client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else websocket.client.host
        ip_check_query = "SELECT 1 FROM banned_ips WHERE ip = $1"
        ip_blocked = await conn.fetchval(ip_check_query, client_ip)

        if ip_blocked:
            valid = False
            message = "IP blocked"


    except Exception as e:
        print("exception: " + str(e), flush=True)
    finally:
        await release_pg_connection(conn)



    await websocket.accept()
    await websocket.send_text(f'{{"cat": "statusmsg", "msg": "stream opened for {username}, id: {id}"}}')

    if not valid:
        await websocket.send_text(f'{{"cat": "statusmsg", "msg": "{message}"}}')
        await websocket.close()
        print(message,flush=True)
        return


    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.add_listener(CHANNEL, lambda *args: asyncio.create_task(notify_ws(args, websocket)))
    await conn.add_listener("whisper_" + str(id), lambda *args: asyncio.create_task(notify_ws_w(args, websocket)))


    try:
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
    if payload == 'exit':
        await websocket.send_text('{"cat": "statusmsg", "msg": "stream closed"}')
        await websocket.close()
    else:
        await websocket.send_text(payload)



async def notify_ws_w(args, websocket: WebSocket):
    _, pid, channel, payload = args
    await websocket.send_text(payload)





from routes import input
from routes import login
from routes import pwmanage
from routes import toplist
from routes.admin import settings
from routes.admin import admin


app.include_router(input.router, tags=["input"], prefix="/api/input", dependencies=[Depends(verify_token)])
app.include_router(login.router, tags=["login"], prefix="/api/login")
app.include_router(pwmanage.router, tags=["pwmanage"], prefix="/api/pwmanage")
app.include_router(toplist.router, tags=["toplist"], prefix="/api/toplist")


app.include_router(settings.router, tags=["settings"], prefix="/api/settings", dependencies=[Depends(verify_token_admin)])
app.include_router(admin.router, tags=["admin"], prefix="/api/admin", dependencies=[Depends(verify_token_admin)])

# Mount the "static" directory to serve HTML/CSS/JS
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/client.html", "r") as f:
        return f.read() 
    

templates = Jinja2Templates(directory="templates")

@app.get("/test/{token}", response_class=HTMLResponse)
async def test_minimal_frontend(request: Request, token : str):
    return templates.TemplateResponse("client.html", {"request": request, "token": token})