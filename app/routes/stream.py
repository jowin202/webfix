from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from db import get_pg_connection, release_pg_connection
import os
import json
import asyncpg

from settings import SettingsManager

router = APIRouter()


DB_CONFIG = {
    "user": os.getenv('POSTGRES_USER'),
    "password": os.getenv('POSTGRES_PASSWORD'),
    "database": os.getenv('POSTGRES_DB'),
    "host": os.getenv('POSTGRES_HOST', 'localhost'),
    "port": os.getenv('POSTGRES_PORT', 5432)
}


@router.websocket("/ws")
async def websocket_endpoint_single_channel(websocket: WebSocket):
    """Traditional mode: one connection, bound to exactly one channel for its
    whole lifetime. Unlike /ws3 there is no subscribe/unsubscribe protocol,
    so the backend can never deliver another channel's activity over this
    connection -- switching channels means the client opens a new one."""
    token = websocket.query_params.get("token")
    announce = websocket.query_params.get("announce", "1").lower() in ("1", "true", "yes")
    try:
        channel_id = int(websocket.query_params.get("channel_id", ""))
    except (TypeError, ValueError):
        await websocket.close(code=1008)
        return

    from_channel_id_raw = websocket.query_params.get("from_channel_id")
    try:
        from_channel_id = int(from_channel_id_raw) if from_channel_id_raw is not None else None
    except (TypeError, ValueError):
        from_channel_id = None

    valid = False
    message = ""
    username = ""
    user_id = -1
    is_guest = False
    conn = None
    try:
        if token is None or token.strip() == "":
            message = "Unknown token"
        else:
            conn = await get_pg_connection()

            result = await conn.fetchrow(
                """
                SELECT id, username, remove_on_logout
                FROM users
                WHERE token = $1
                AND token <> ''
                """,
                token,
            )
            if result:
                valid = True
                username = result['username']
                user_id = int(result['id'])
                is_guest = bool(result['remove_on_logout'])
            else:
                message = "Unknown token"

            if valid:
                has_access = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM channels c
                        WHERE c.id = $1
                        AND (
                            c.always_available = true
                            OR EXISTS (
                                SELECT 1
                                FROM channel_members cm
                                WHERE cm.user_id = $2
                                AND cm.channel_id = c.id
                            )
                        )
                    )
                    """,
                    channel_id,
                    user_id,
                )
                if not has_access:
                    valid = False
                    message = "No access to that channel."

            x_forwarded_for = websocket.headers.get("x-forwarded-for")
            client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else websocket.client.host
            ip_blocked = await conn.fetchval("SELECT 1 FROM banned_ips WHERE ip = $1", client_ip)
            if ip_blocked:
                valid = False
                message = "IP blocked"

            if valid:
                await conn.execute(
                    "SELECT pg_notify($1, $2)",
                    f"whisper_{user_id}",
                    json.dumps({'cat': 'statusmsg', 'msg': 'double login detected'}),
                )
                await conn.execute("SELECT pg_notify($1, $2)", f"whisper_{user_id}", "exit")
    except Exception as e:
        print("exception: " + str(e), flush=True)
        await websocket.close()
        return
    finally:
        if conn is not None:
            await release_pg_connection(conn)

    await websocket.accept()

    if not valid:
        await websocket.send_text(f'{{"cat": "statusmsg", "msg": "{message}"}}')
        await websocket.close()
        return

    listen_conn = await asyncpg.connect(**DB_CONFIG)
    channel_topic = f"channel_{channel_id}"
    whisper_topic = f"whisper_{user_id}"

    async def listener(*args):
        await notify_ws_single(args, websocket)

    await listen_conn.add_listener("global", listener)
    await listen_conn.add_listener(channel_topic, listener)
    await listen_conn.add_listener(whisper_topic, listener)

    from_channel_name = None
    if from_channel_id is not None:
        from_channel_name = await listen_conn.fetchval("SELECT name FROM channels WHERE id = $1", from_channel_id)

    enter_payload = {"cat": "userenters", "username": username, "channel": channel_id}
    if from_channel_name:
        enter_payload["other_channel_name"] = from_channel_name
    await listen_conn.execute("SELECT pg_notify($1, $2)", channel_topic, json.dumps(enter_payload))

    left_already_sent = False

    try:
        manager = SettingsManager()
        announcement = (manager.get_setting("announcement_general") or "").replace("$USER", username) if announce else ""
        announcement_guests = (manager.get_setting("announcement_guests") or "").replace("$USER", username) if announce else ""
        announcement_registered = (manager.get_setting("announcement_registered_users") or "").replace("$USER", username) if announce else ""

        if announcement:
            await websocket.send_text(json.dumps({"cat": "announcement", "msg": announcement}))

        if is_guest and announcement_guests:
            await websocket.send_text(json.dumps({"cat": "announcement", "msg": announcement_guests}))
        elif announcement_registered:
            await websocket.send_text(json.dumps({"cat": "announcement", "msg": announcement_registered}))

        while True:
            raw_msg = await websocket.receive_text()

            try:
                cmd = json.loads(raw_msg)
            except Exception:
                continue

            if not isinstance(cmd, dict) or cmd.get("action") != "switch_leave":
                continue

            try:
                to_channel_id = int(cmd.get("to_channel_id"))
            except (TypeError, ValueError):
                continue

            to_channel_name = await listen_conn.fetchval("SELECT name FROM channels WHERE id = $1", to_channel_id)
            leave_payload = {"cat": "userleft", "username": username, "channel": channel_id}
            if to_channel_name:
                leave_payload["other_channel_name"] = to_channel_name
            await listen_conn.execute("SELECT pg_notify($1, $2)", channel_topic, json.dumps(leave_payload))
            left_already_sent = True

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("WebSocket error:", e)
    finally:
        if not left_already_sent:
            try:
                await listen_conn.execute(
                    "SELECT pg_notify($1, $2)",
                    channel_topic,
                    json.dumps({"cat": "userleft", "username": username, "channel": channel_id}),
                )
            except Exception:
                pass
        for topic in (channel_topic, "global", whisper_topic):
            try:
                await listen_conn.remove_listener(topic, listener)
            except Exception:
                pass
        await listen_conn.close()


async def notify_ws_single(args, websocket: WebSocket):
    _, _, _, payload = args

    if payload == 'exit':
        try:
            await websocket.send_text('{"cat": "statusmsg", "msg": "stream closed"}')
        except Exception:
            pass
        await websocket.close()
        return

    # "add <id>" / "remove <id>" are channel-membership hints meant for /ws3's
    # auto-subscribe loop; this endpoint is bound to a single channel and has
    # nothing dynamic to do with them.
    if payload.startswith("add ") or payload.startswith("remove "):
        return

    try:
        await websocket.send_text(payload)
    except Exception:
        pass


@router.websocket("/ws3")
async def websocket_endpoint_multi_channel(websocket: WebSocket):
    token = websocket.query_params.get("token")
    manual_subscribe = websocket.query_params.get("manual_subscribe", "0").lower() in ("1", "true", "yes")
    auto_subscribe = not manual_subscribe

    valid = False
    message = ""
    username = ""
    user_id = -1
    channel_ids = []
    is_guest = False
    conn = None
    try:
        if token is None or token.strip() == "":
            message = "Unknown token"
        else:
            conn = await get_pg_connection()

            result = await conn.fetchrow(
                """
                SELECT id, username, remove_on_logout
                FROM users
                WHERE token = $1
                AND token <> ''
                """,
                token,
            )
            if result:
                valid = True
                username = result['username']
                user_id = int(result['id'])
                is_guest = bool(result['remove_on_logout'])
            else:
                message = "Unknown token"

            result = await conn.fetch(
                """
                SELECT id
                FROM channels
                WHERE always_available = true
                UNION
                SELECT channel_id AS id
                FROM channel_members
                WHERE user_id = $1
                """,
                user_id,
            )
            if result:
                channel_ids = [int(row['id']) for row in result]

            x_forwarded_for = websocket.headers.get("x-forwarded-for")
            client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else websocket.client.host
            ip_blocked = await conn.fetchval("SELECT 1 FROM banned_ips WHERE ip = $1", client_ip)
            if ip_blocked:
                valid = False
                message = "IP blocked"

            if valid:
                await conn.execute(
                    "SELECT pg_notify($1, $2)",
                    f"whisper_{user_id}",
                    json.dumps({'cat': 'statusmsg', 'msg': 'double login detected'}),
                )
                await conn.execute("SELECT pg_notify($1, $2)", f"whisper_{user_id}", "exit")
    except Exception as e:
        print("exception: " + str(e), flush=True)
        await websocket.close()
        return
    finally:
        if conn is not None:
            await release_pg_connection(conn)

    await websocket.accept()

    if not valid:
        await websocket.send_text(f'{{"cat": "statusmsg", "msg": "{message}"}}')
        await websocket.close()
        return

    listen_conn = await asyncpg.connect(**DB_CONFIG)

    async def can_access_channel(channel_id: int) -> bool:
        access_conn = await get_pg_connection()
        try:
            return bool(
                await access_conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM channels c
                        WHERE c.id = $1
                        AND (
                            c.always_available = true
                            OR EXISTS (
                                SELECT 1
                                FROM channel_members cm
                                WHERE cm.user_id = $2
                                AND cm.channel_id = c.id
                            )
                        )
                    )
                    """,
                    channel_id,
                    user_id,
                )
            )
        finally:
            await release_pg_connection(access_conn)

    async def add_channel(channel_id: int):
        nonlocal current_channel_listeners
        if channel_id in current_channel_listeners:
            return

        payload = json.dumps({"cat": "userenters", "username": username, "channel": channel_id})
        listener = create_listener(websocket, add_channel, remove_channel)
        current_channel_listeners[channel_id] = listener

        await listen_conn.add_listener("channel_" + str(channel_id), listener)
        await listen_conn.execute("SELECT pg_notify($1, $2)", "channel_" + str(channel_id), payload)

    async def remove_channel(channel_id: int):
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
            await notify_ws(args, websocket, add_channel_callback, remove_channel_callback, auto_subscribe)
        return listener

    current_channel_listeners = {}
    global_listener = create_listener(websocket, add_channel, remove_channel)
    whisper_listener = create_listener(websocket, add_channel, remove_channel)

    await listen_conn.add_listener("global", global_listener)
    if auto_subscribe:
        for channel_id in channel_ids:
            await add_channel(channel_id)
    await listen_conn.add_listener("whisper_" + str(user_id), whisper_listener)

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
            raw_msg = await websocket.receive_text()
            if not manual_subscribe:
                continue

            try:
                cmd = json.loads(raw_msg)
            except Exception:
                continue

            if not isinstance(cmd, dict):
                continue

            action = cmd.get("action")
            try:
                channel_id = int(cmd.get("channel"))
            except Exception:
                continue

            if action == "subscribe":
                if await can_access_channel(channel_id):
                    await add_channel(channel_id)
                else:
                    await websocket.send_text(json.dumps({
                        "cat": "statusmsg",
                        "channel": channel_id,
                        "msg": "No access to that channel."
                    }))
            elif action == "unsubscribe":
                await remove_channel(channel_id)

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
            await listen_conn.remove_listener("whisper_" + str(user_id), whisper_listener)
        except Exception:
            pass
        await listen_conn.close()


async def notify_ws(args, websocket: WebSocket, add_channel_callback, remove_channel_callback, auto_subscribe: bool):
    _, _, _, payload = args

    if payload == 'exit':
        try:
            await websocket.send_text('{"cat": "statusmsg", "msg": "stream closed"}')
        except Exception:
            pass
        await websocket.close()
        return

    if payload.startswith("add "):
        try:
            channel_id = int(payload.split()[1])
            if auto_subscribe:
                await add_channel_callback(channel_id)
            else:
                await websocket.send_text(json.dumps({
                    "cat": "channel_access_added",
                    "channel": channel_id
                }))
        except Exception:
            pass
        return

    if payload.startswith("remove "):
        try:
            channel_id = int(payload.split()[1])
            await remove_channel_callback(channel_id)
            await websocket.send_text(json.dumps({
                "cat": "channel_access_removed",
                "channel": channel_id
            }))
        except Exception:
            pass
        return

    try:
        await websocket.send_text(payload)
    except Exception:
        pass
