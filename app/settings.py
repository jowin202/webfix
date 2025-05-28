
from db import get_pg_connection, release_pg_connection
from typing import Union, Literal, List

SettingType = Literal["string", "int", "bool"]

class SettingsManager:
    _instance = None
    _initialized = False

    settings = {}
    html_names = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
        return cls._instance

    async def initialize(self):
        if self._initialized:
            return
        await self._load_settings()
        self._initialized = True

    async def _load_settings(self):
        conn = await get_pg_connection()
        try:
            rows = await conn.fetch("SELECT key, value_str FROM settings_str")
            self.settings.update({row['key']: row['value_str'] for row in rows})

            rows = await conn.fetch("SELECT key, value_int FROM settings_int")
            self.settings.update({row['key']:  row['value_int'] for row in rows})

            rows = await conn.fetch("SELECT key, value_bool FROM settings_bool")
            self.settings.update({row['key']:  row['value_bool'] for row in rows})

            rows = await conn.fetch("SELECT username,username_html FROM users")
            self.html_names.update({row['username']:  row['username_html'] for row in rows})
        except:
            pass
        finally:
            await release_pg_connection(conn)


    def get_setting(self, key):
        if key not in self.settings:
            return None
        else:
            return self.settings[key]

        
    async def set_setting(self, key: str, value: Union[str, int, bool]):
        conn = await get_pg_connection()
        try:
            if isinstance(value, str):
                await conn.execute(f"""INSERT INTO settings_str (key, value_str) VALUES ('{key}', '{value}') ON CONFLICT(key) DO UPDATE SET value_str = EXCLUDED.value_str;""")
            elif isinstance(value, bool):
                await conn.execute(f"""INSERT INTO settings_bool (key, value_bool) VALUES ('{key}', '{value}') ON CONFLICT(key) DO UPDATE SET value_bool = EXCLUDED.value_bool;""")
            elif isinstance(value, int):
                await conn.execute(f"""INSERT INTO settings_int (key, value_int) VALUES ('{key}', '{value}') ON CONFLICT(key) DO UPDATE SET value_int = EXCLUDED.value_int;""")
        except:
            pass
        finally:
            await self._load_settings()
            await release_pg_connection(conn)


    async def set_setting_if_not_exists(self, key: str, value: Union[str, int, bool]):
        conn = await get_pg_connection()
        try:
            if isinstance(value, str):
                await conn.execute(f"""INSERT INTO settings_str (key, value_str) VALUES ('{key}', '{value}') ON CONFLICT(key) DO NOTHING;""")
            elif isinstance(value, bool):
                await conn.execute(f"""INSERT INTO settings_bool (key, value_bool) VALUES ('{key}', '{value}') ON CONFLICT(key) DO NOTHING;""")
            elif isinstance(value, int):
                await conn.execute(f"""INSERT INTO settings_int (key, value_int) VALUES ('{key}', '{value}') ON CONFLICT(key) DO NOTHING;""")
        except:
            pass
        finally:
            await self._load_settings()
            await release_pg_connection(conn)


    async def get_username_html(self, username):
        if username not in self.settings:
            return username
        else:
            return self.html_names[username]

    async def set_username_html(self, username: str, value: str):
        conn = await get_pg_connection()
        try:
            await conn.execute(f"""INSERT INTO users (username, username_html) VALUES ('{username}', '{value}') ON CONFLICT(key) DO UPDATE SET username_html = EXCLUDED.username_html;""")
        except:
            pass
        finally:
            await self._load_settings()
            await release_pg_connection(conn)

