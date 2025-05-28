
from fastapi import Depends, Request, HTTPException

from db import get_pg_connection, release_pg_connection


# security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login/")

async def verify_token(request: Request, token: str = Depends(oauth2_scheme)):
    conn = await get_pg_connection()

    x_forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else request.client.host

    ip_check_query = "SELECT 1 FROM banned_ips WHERE ip = $1"
    ip_blocked = await conn.fetchval(ip_check_query, client_ip)

    query = '''
        SELECT id 
        FROM users 
        WHERE token = $1 
    '''
    result = await conn.fetchrow(query, token)
    await release_pg_connection(conn)

    if ip_blocked:
        raise HTTPException(status_code=403, detail="Your IP is blocked.")
    
    valid = False
    if result: # todo result as admin
        valid = True

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    request.state.user_id = result['id']
    request.state.admin = 0
    return token


async def verify_token_admin(request: Request, token: str = Depends(oauth2_scheme)):
    conn = await get_pg_connection()
    query = '''
        SELECT id, admin 
        FROM users 
        WHERE token = $1 AND admin > 2
    '''
    result = await conn.fetchrow(query, token)
    await release_pg_connection(conn)

    valid = False
    if result: # todo result as admin
        valid = True

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid token")
    request.state.user_id = result['id']
    request.state.admin = result['admin']
    return token