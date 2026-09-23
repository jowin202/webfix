from typing import Dict, Set

_channel_presence: Dict[int, Set[int]] = {}


def add_presence(channel_id: int, user_id: int):
    _channel_presence.setdefault(channel_id, set()).add(user_id)


def remove_presence(channel_id: int, user_id: int):
    users = _channel_presence.get(channel_id)
    if users is None:
        return
    users.discard(user_id)
    if not users:
        _channel_presence.pop(channel_id, None)


def get_presence(channel_id: int) -> Set[int]:
    return set(_channel_presence.get(channel_id, set()))


def get_connected_user_ids() -> Set[int]:
    """Union of every user_id with a live websocket connection, in any channel."""
    connected: Set[int] = set()
    for users in _channel_presence.values():
        connected.update(users)
    return connected
