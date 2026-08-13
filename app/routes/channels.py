import json
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import get_pg_connection, release_pg_connection

router = APIRouter()

NotifyScope = Literal["private", "channel", "global"]
STATUS_SENDER = "ChatBot"


class CreateChannelRequest(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    invite_only: bool = False


class JoinChannelRequest(BaseModel):
    password: Optional[str] = None


class InviteChannelRequest(BaseModel):
    channel_id: int
    username: str


class SwitchChannelRequest(BaseModel):
    to_channel_id: int
    from_channel_id: Optional[int] = None


async def _notify_channel_access(conn, user_id: int, action: str, channel_id: int):
    await conn.execute("SELECT pg_notify($1, $2)", f"whisper_{user_id}", f"{action} {channel_id}")


async def _notify_status_message(
    conn,
    message: str,
    scope: NotifyScope,
    channel_id: Optional[int] = None,
    user_id: Optional[int] = None,
    reload_channels: bool = False,
):
    payload = {"cat": "statusmsg", "username": STATUS_SENDER, "msg": message}
    if channel_id is not None:
        payload["channel"] = channel_id
    if reload_channels:
        payload["reload_channels"] = True

    if scope == "private":
        if user_id is None:
            return
        target = f"whisper_{user_id}"
    elif scope == "channel":
        if channel_id is None:
            return
        target = f"channel_{channel_id}"
    else:
        target = "global"

    await conn.execute("SELECT pg_notify($1, $2)", target, json.dumps(payload))


async def _delete_channel_if_empty(conn, channel_id: int):
    return await conn.fetchval(
        """
        DELETE FROM channels c
        WHERE c.id = $1
          AND COALESCE(c.always_available, false) = false
          AND NOT EXISTS (
              SELECT 1 FROM channel_members cm WHERE cm.channel_id = c.id
          )
        RETURNING c.id
        """,
        channel_id,
    )


async def _channel_with_access_flags(conn, channel_id: int, user_id: int):
    return await conn.fetchrow(
        """
        SELECT
            c.id,
            c.name,
            c.owner,
            c.always_available,
            COALESCE(c.invite_only, false) AS invite_only,
            COALESCE(c.password, '') AS password,
            EXISTS (
                SELECT 1
                FROM channel_members cm
                WHERE cm.channel_id = c.id
                AND cm.user_id = $2
            ) AS is_member,
            EXISTS (
                SELECT 1
                FROM channel_invites ci
                WHERE ci.channel_id = c.id
                AND ci.user_id = $2
            ) AS is_invited
        FROM channels c
        WHERE c.id = $1
        """,
        channel_id,
        user_id,
    )


async def _username_by_id(conn, user_id: int) -> str:
    username = await conn.fetchval("SELECT username FROM users WHERE id = $1", user_id)
    return username or f"User {user_id}"


@router.get("/list/")
async def list_channels(request: Request):
    conn = await get_pg_connection()
    try:
        result = await conn.fetch(
            """
            SELECT
                c.id,
                c.name,
                c.always_available,
                COALESCE(c.invite_only, false) AS invite_only,
                (COALESCE(c.password, '') <> '') AS has_password,
                (c.owner = $1) AS is_owner,
                (
                    c.always_available = true
                    OR EXISTS (
                        SELECT 1
                        FROM channel_members cm
                        WHERE cm.channel_id = c.id
                        AND cm.user_id = $1
                    )
                ) AS is_member,
                EXISTS (
                    SELECT 1
                    FROM channel_invites ci
                    WHERE ci.channel_id = c.id
                    AND ci.user_id = $1
                ) AS is_invited
            FROM channels c
            WHERE c.always_available = true
               OR c.id = 1
               OR COALESCE(c.invite_only, false) = false
               OR EXISTS (
                    SELECT 1
                    FROM channel_members cm
                    WHERE cm.channel_id = c.id
                    AND cm.user_id = $1
               )
               OR EXISTS (
                    SELECT 1
                    FROM channel_invites ci
                    WHERE ci.channel_id = c.id
                    AND ci.user_id = $1
               )
            ORDER BY c.id
            """,
            request.state.user_id,
        )
        return result
    finally:
        await release_pg_connection(conn)


@router.post("/create_channel/")
async def create_channel(
    request: Request,
    data: Optional[CreateChannelRequest] = None,
    name: Optional[str] = None,
    password: Optional[str] = None,
    invite_only: Optional[bool] = None,
):
    conn = await get_pg_connection()
    try:
        payload_name = (name if name is not None else (data.name if data else None)) or ""
        payload_password = (password if password is not None else (data.password if data else None)) or ""
        payload_invite_only = invite_only if invite_only is not None else (data.invite_only if data else False)

        normalized_name = payload_name.strip()
        if not normalized_name or len(normalized_name) < 2:
            raise HTTPException(status_code=400, detail="Channel name must have at least 2 characters.")
        if len(normalized_name) > 64:
            raise HTTPException(status_code=400, detail="Channel name is too long.")

        channel_id = await conn.fetchval(
            """
            INSERT INTO channels (name, always_available, password, owner, invite_only)
            VALUES ($1, false, $2, $3, $4)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            normalized_name,
            payload_password.strip(),
            request.state.user_id,
            payload_invite_only,
        )

        if channel_id is None:
            raise HTTPException(status_code=409, detail="Channel already exists.")

        await conn.execute(
            """
            INSERT INTO channel_members (user_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            request.state.user_id,
            channel_id,
        )

        await _notify_channel_access(conn, request.state.user_id, "add", channel_id)
        actor = await _username_by_id(conn, request.state.user_id)
        await _notify_status_message(
            conn,
            f'{actor} created channel "{normalized_name}".',
            "global",
            reload_channels=True,
        )
        return {"result": True, "channel_id": channel_id}
    finally:
        await release_pg_connection(conn)


@router.post("/join/{channel_id}/")
async def join_channel(
    channel_id: int,
    request: Request,
    data: Optional[JoinChannelRequest] = None,
    password: Optional[str] = None,
):
    conn = await get_pg_connection()
    try:
        channel = await _channel_with_access_flags(conn, channel_id, request.state.user_id)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found.")

        if channel["is_member"] or channel["always_available"]:
            return {"result": True, "already_member": bool(channel["is_member"])}

        if channel["invite_only"] and not channel["is_invited"]:
            raise HTTPException(status_code=403, detail="Invitation required.")

        expected_password = channel["password"] or ""
        provided_password = ((password if password is not None else (data.password if data else None)) or "").strip()
        if expected_password and expected_password != provided_password:
            raise HTTPException(status_code=403, detail="Wrong password.")

        await conn.execute(
            """
            INSERT INTO channel_members (user_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            request.state.user_id,
            channel_id,
        )

        await conn.execute(
            """
            DELETE FROM channel_invites
            WHERE user_id = $1
            AND channel_id = $2
            """,
            request.state.user_id,
            channel_id,
        )

        await _notify_channel_access(conn, request.state.user_id, "add", channel_id)
        actor = await _username_by_id(conn, request.state.user_id)
        await _notify_status_message(
            conn,
            f'{actor} joined channel "{channel["name"]}".',
            "global",
            reload_channels=True,
        )
        return {"result": True, "channel_id": channel_id}
    finally:
        await release_pg_connection(conn)


@router.post("/add_channel/{channel_id}/")
async def add_channel_by_id(channel_id: int, request: Request):
    return await join_channel(channel_id, request, JoinChannelRequest())


@router.post("/switch/")
async def switch_channel(data: SwitchChannelRequest, request: Request):
    conn = await get_pg_connection()
    try:
        to_channel = await _channel_with_access_flags(conn, data.to_channel_id, request.state.user_id)
        if not to_channel or not (to_channel["is_member"] or to_channel["always_available"]):
            raise HTTPException(status_code=403, detail="No access to that channel.")

        actor = await _username_by_id(conn, request.state.user_id)
        message = f'{actor} switched to channel "{to_channel["name"]}".'

        if data.from_channel_id is not None and data.from_channel_id != data.to_channel_id:
            await _notify_status_message(conn, message, "channel", channel_id=data.from_channel_id)
        await _notify_status_message(conn, message, "channel", channel_id=data.to_channel_id)

        return {"result": True}
    finally:
        await release_pg_connection(conn)


@router.post("/remove_channel/{channel_id}/")
async def remove_channel_by_id(channel_id: int, request: Request):
    conn = await get_pg_connection()
    try:
        channel = await conn.fetchrow(
            "SELECT id, name, owner, always_available FROM channels WHERE id = $1",
            channel_id,
        )
        if channel is None:
            raise HTTPException(status_code=404, detail="Channel not found.")

        delete_result = await conn.execute(
            """
            DELETE FROM channel_members
            WHERE user_id = $1
            AND channel_id = $2
            """,
            request.state.user_id,
            channel_id,
        )

        deleted_channel_id = await _delete_channel_if_empty(conn, channel_id)
        await _notify_channel_access(conn, request.state.user_id, "remove", channel_id)

        actor = await _username_by_id(conn, request.state.user_id)
        if delete_result.endswith("1"):
            await _notify_status_message(
                conn,
                f'{actor} left channel "{channel["name"]}".',
                "global",
                reload_channels=True,
            )
        if deleted_channel_id:
            await _notify_status_message(
                conn,
                f'Channel "{channel["name"]}" was deleted (no members left).',
                "global",
                reload_channels=True,
            )

        return {"result": True, "channel_deleted": bool(deleted_channel_id)}
    finally:
        await release_pg_connection(conn)


@router.post("/invite/")
async def invite_to_channel(
    request: Request,
    data: Optional[InviteChannelRequest] = None,
    channel_id: Optional[int] = None,
    username: Optional[str] = None,
):
    conn = await get_pg_connection()
    try:
        raw_channel_id = data.channel_id if data else channel_id
        if raw_channel_id is None:
            raise HTTPException(status_code=400, detail="channel_id is required.")
        payload_channel_id = int(raw_channel_id)
        payload_username = (data.username if data else username or "").strip()
        if not payload_username:
            raise HTTPException(status_code=400, detail="Username is required.")

        channel = await conn.fetchrow(
            "SELECT id, name, owner, always_available FROM channels WHERE id = $1",
            payload_channel_id,
        )
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found.")

        if channel["owner"] != request.state.user_id:
            raise HTTPException(status_code=403, detail="Only owner can invite users.")

        target_user_id = await conn.fetchval(
            "SELECT id FROM users WHERE LOWER(username) = LOWER($1)",
            payload_username,
        )
        if target_user_id is None:
            raise HTTPException(status_code=404, detail="User not found.")

        if target_user_id == request.state.user_id:
            raise HTTPException(status_code=400, detail="Cannot invite yourself.")

        await conn.execute(
            """
            INSERT INTO channel_invites (user_id, channel_id, invited_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, channel_id) DO NOTHING
            """,
            target_user_id,
            payload_channel_id,
            request.state.user_id,
        )

        # Trigger client refresh for the invited user.
        await _notify_channel_access(conn, target_user_id, "add", payload_channel_id)
        await _notify_status_message(
            conn,
            f'You were invited to channel "{channel["name"]}".',
            "private",
            user_id=target_user_id,
            reload_channels=True,
        )
        return {"result": True}
    finally:
        await release_pg_connection(conn)
