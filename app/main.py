import asyncio
import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Depends

from fastapi.templating import Jinja2Templates


import os 
import json

from contextlib import asynccontextmanager
from datetime import datetime

from security import verify_token, verify_token_admin
from db import pg_db_init, get_pg_connection, initialize_connection_pool, release_pg_connection

from settings import SettingsManager
from timeout import timeout_check




# Database config
DB_CONFIG = {
    "user": os.getenv('POSTGRES_USER'),
    "password": os.getenv('POSTGRES_PASSWORD'),
    "database": os.getenv('POSTGRES_DB'),
    "host": os.getenv('POSTGRES_HOST', 'localhost'),
    "port": os.getenv('POSTGRES_PORT', 5432) 
}

import time
@asynccontextmanager
async def lifespan(app: FastAPI):
    db_is_ready = False
    while not db_is_ready:
        try:
            time.sleep(1)
            await initialize_connection_pool()
            await pg_db_init()
            db_is_ready = True
        except:
            pass


    manager = SettingsManager()
    await manager.initialize()

    await manager.set_setting_if_not_exists("allow_guest_login", True)
    await manager.set_setting_if_not_exists("activate_timeout", True)
    await manager.set_setting_if_not_exists("mandatory_user_verification", True)
    await manager.set_setting_if_not_exists("user_verification_mail", True)
    await manager.set_setting_if_not_exists("user_verification_fediverse", True)

    await manager.set_setting_if_not_exists("timeout_time", 180)
    await manager.set_setting_if_not_exists("pw_recovery_token_valid_time", 600)
    await manager.set_setting_if_not_exists("pw_min_len", 3)
    await manager.set_setting_if_not_exists("fido2_challenge_valid_time", 60)
    
    await manager.set_setting_if_not_exists("announcement_general", "Welcome to our chat, $USER! ")
    await manager.set_setting_if_not_exists("announcement_guests", "Hello $USER, Please register your username!")
    await manager.set_setting_if_not_exists("announcement_registered_users", "Welcome and thanks for registering, $USER!")
    await manager.set_setting_if_not_exists("announcement_team", "Who is online at 9pm?")
    

    asyncio.create_task(timeout_check())

    yield # this is mandatory

app = FastAPI(title="Webfix API", lifespan=lifespan)





from routes import stream
from routes import input
from routes import channels
from routes import login
from routes import register
from routes import pwmanage
from routes import data
from routes import fido2
from routes import activationlinks
from routes.admin import settings
from routes.admin import userdb
from routes.admin import admin


app.include_router(stream.router, tags=["stream"], prefix="/api/stream")
app.include_router(input.router, tags=["input"], prefix="/api/input", dependencies=[Depends(verify_token)])
app.include_router(channels.router, tags=["channels"], prefix="/api/channels", dependencies=[Depends(verify_token)])
app.include_router(login.router, tags=["login"], prefix="/api/login")
app.include_router(register.router, tags=["register"], prefix="/api/register")
app.include_router(pwmanage.router, tags=["pwmanage"], prefix="/api/pwmanage")
app.include_router(data.router, tags=["data"], prefix="/api/data", dependencies=[Depends(verify_token)])
app.include_router(fido2.router, tags=["fido2"], prefix="/api/fido2")
app.include_router(activationlinks.router, tags=["activationlinks"], prefix="")


app.include_router(settings.router, tags=["admin_settings"], prefix="/api/admin/settings", dependencies=[Depends(verify_token_admin)])
app.include_router(userdb.router, tags=["admin_user_database"], prefix="/api/admin/userdb", dependencies=[Depends(verify_token_admin)])
app.include_router(admin.router, tags=["admin"], prefix="/api/admin", dependencies=[Depends(verify_token_admin)])


app.mount("/", StaticFiles(directory="static", html=True), name="static-root")

@app.middleware("http")
async def spa_fallback(request: Request, call_next):

    # Paths that should NOT fall back to index.html
    passthrough_prefixes = (
        "/api", "/activate", "/docs", "/redoc", "/openapi.json"
    )
    if (
        request.url.path.startswith(passthrough_prefixes)
        or os.path.isfile(f"static{request.url.path}")
    ):
        return await call_next(request)

    # Frontend2 is mounted under /new
    if request.url.path == "/new" or request.url.path.startswith("/new/"):
        with open("static/new/index.html") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)

    # Frontend1 for anything else
    with open("static/index.html") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)
