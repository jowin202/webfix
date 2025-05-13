import asyncio
import asyncpg
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocketDisconnect, Depends

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
    await manager.set_setting_if_not_exists("mandatory_user_verification", False)

    await manager.set_setting_if_not_exists("timeout_time", 600)
    
    await manager.set_setting_if_not_exists("announcement_general", "Welcome to our chat!")
    await manager.set_setting_if_not_exists("announcement_guests", "Please register your username!")
    await manager.set_setting_if_not_exists("announcement_registered_users", "Welcome and thanks for registering!")
    await manager.set_setting_if_not_exists("announcement_team", "Who is online at 9pm?")
    

    yield # this is mandatory

app = FastAPI(title="Webfix API", lifespan=lifespan)






@app.post("/exit")
async def send_notification():
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute(f"NOTIFY {CHANNEL}, 'exit'")
    await conn.close()
    return {"status": "signal sent" }


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


async def notify_ws(args, websocket: WebSocket):
    _, pid, channel, payload = args
    if payload == 'exit':
        await websocket.send_text('{"cat": "statusmsg", "msg": "stream closed"}')
        await websocket.close()
    else:
        await websocket.send_text(payload)





from routes import input
from routes import login
from routes import toplist
from routes.admin import settings


app.include_router(input.router, tags=["input"], prefix="/api/input", dependencies=[Depends(verify_token)])
app.include_router(login.router, tags=["login"], prefix="/api/login")
app.include_router(toplist.router, tags=["toplist"], prefix="/api/toplist")


app.include_router(settings.router, tags=["admin"], prefix="/api/admin", dependencies=[Depends(verify_token_admin)])

# Mount the "static" directory to serve HTML/CSS/JS
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/client.html", "r") as f:
        return f.read() 