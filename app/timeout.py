
from settings import SettingsManager
from db import get_pg_connection, release_pg_connection
from routes.login import logout_token
import asyncio

async def timeout_check():
    refresh_intervall = 10
    manager = SettingsManager()
    while True:
        #print("timeout check", flush=True)
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

        #print("refresh_intervall", flush=True)
        #print(refresh_intervall, flush=True)
        await release_pg_connection(conn)
        await asyncio.sleep(refresh_intervall)
