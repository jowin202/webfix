from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from io import BytesIO
from pydantic import BaseModel
from helper import token_generate
from db import get_pg_connection, release_pg_connection
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from typing import Dict, Any, List
from settings import SettingsManager

router = APIRouter()



manager = SettingsManager()

@router.post("/set_settings/")
async def set_settings(settings: Dict[str, Any]):
    for key, value in settings.items():
        if isinstance(value, (str, int, bool)):
            await manager.set_setting(key, value)
        else:
            return {"error": f"Unsupported value type for key '{key}': {type(value).__name__}"}
    return {"status": "success"}


@router.post("/get_settings/")
async def get_settings(keys: List[str]):
    result = {}
    for key in keys:
       result[key] = manager.get_setting(key)
    return result