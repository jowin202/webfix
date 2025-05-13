
from helper import get_pg_connection, release_pg_connection
from typing import Union, Literal

SettingType = Literal["string", "int", "bool"]

class SettingsManager:
    _instance = None
    _initialized = False

    settings = {}

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

        except:
            pass
        finally:
            await release_pg_connection(conn)


    async def get_setting(self, key):
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
            if isinstance(value, int):
                await conn.execute(f"""INSERT INTO settings_int (key, value_int) VALUES ('{key}', '{value}') ON CONFLICT(key) DO UPDATE SET value_int = EXCLUDED.value_int;""")
        except:
            pass
        finally:
            await self._load_settings()
            await release_pg_connection(conn)


