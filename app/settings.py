
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
            rows = await conn.fetch("SELECT key, value_str, value_int, value_bool FROM settings")
            self.settings = {row['key']: {
                'value_str': row['value_str'],
                'value_int': row['value_int'],
                'value_bool': row['value_bool']
            } for row in rows}
        except:
            pass
        finally:
            await release_pg_connection(conn)


    async def get_setting(self, key: str, value_type: SettingType) -> Union[str, int, bool, None]:
        if key not in self.settings:
            return None
        if value_type is str:
            return self.settings[key]['value_str']
        elif value_type is bool:
            return self.settings[key]['value_bool']
        elif value_type is int:
            return self.settings[key]['value_int']
        else:
            raise ValueError("Unsupported type")

        print(self.settings[key],flush=True)
        #if type_ is bool:
        #    return self.settings[key]
        
    async def set_setting(self, key: str, value: Union[str, int, bool]):
        if isinstance(value, str):
            value_type = "value_str"
        elif isinstance(value, bool):
            value_type = "value_bool"
            value = "true" if value else "false"
        elif isinstance(value, int):
            value_type = "value_int"
        else:
            raise ValueError("Unsupported type")

        conn = await get_pg_connection()
        try:
            await conn.execute(f"""INSERT INTO settings (key, {value_type}) VALUES ('{key}', '{value}') ON CONFLICT(key) DO UPDATE SET {value_type} = excluded.{value_type}""")
            await self._load_settings()
        except:
            pass
        finally:
            await release_pg_connection(conn)


