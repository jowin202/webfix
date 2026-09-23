
from settings import SettingsManager
from db import get_pg_connection, release_pg_connection
from routes.login import logout_token
from presence import get_connected_user_ids
import asyncio

async def timeout_check():
    refresh_intervall = 10
    manager = SettingsManager()
    while True:
        #print("timeout check", flush=True)
        conn = await get_pg_connection()

        # Users with no live websocket connection anywhere (tab closed, laptop
        # asleep, network gone) are timed out far more aggressively than the
        # normal chat-inactivity timeout below -- otherwise they keep showing
        # as "online" (token != '') for the full timeout_time even though
        # nothing is actually connected.
        connected_ids = list(get_connected_user_ids())
        timeout_time = str(manager.get_setting("timeout_time"))
        disconnected_timeout_time = str(manager.get_setting("disconnected_timeout_time"))

        result = await conn.fetch("""
            SELECT id, username, token
            FROM users
            WHERE last_posted IS NOT NULL
            AND token != ''
            AND (
                (id = ANY($2::int[]) AND last_posted < NOW() - ($1 || ' seconds')::interval)
                OR
                (NOT (id = ANY($2::int[])) AND last_posted < NOW() - ($3 || ' seconds')::interval)
            )
        """, timeout_time, connected_ids, disconnected_timeout_time)
        for row in result:
            msg = '{"cat": "statusmsg", "msg": "Timeout"}'
            await conn.execute(f"NOTIFY whisper_{row['id']}, '{msg}' ")
            await logout_token(row['token']) # from endpoint


        row = await conn.fetchrow("""
            SELECT MIN(
                (last_posted + (CASE WHEN id = ANY($2::int[]) THEN $1 ELSE $3 END || ' seconds')::interval) - NOW()
            ) AS remaining
            FROM users
            WHERE token != ''
            AND last_posted IS NOT NULL
            AND (last_posted + (CASE WHEN id = ANY($2::int[]) THEN $1 ELSE $3 END || ' seconds')::interval) > NOW()
                                           """, timeout_time, connected_ids, disconnected_timeout_time)

        if row and row['remaining']:
            refresh_intervall = int(row['remaining'].total_seconds())+5 # 5 sec tolerance for testing
        else:
            refresh_intervall = int(min(manager.get_setting("timeout_time"), manager.get_setting("disconnected_timeout_time"))/2)  # or 0 or some fallback

        #print("refresh_intervall", flush=True)
        #print(refresh_intervall, flush=True)
        await release_pg_connection(conn)
        await asyncio.sleep(refresh_intervall)
