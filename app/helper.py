
import string
import random
import asyncpg
import os
from fastapi import Depends, Request, HTTPException

import smtplib
from email.message import EmailMessage

from datetime import datetime
from mastodon import Mastodon



def token_generate():
    password = []
    characterList = ""
    characterList += string.ascii_letters
    characterList += string.digits
    for i in range(32):
        randomchar = random.choice(characterList)
        password.append(randomchar)
    return str("".join(password))



connection_pool = None

async def initialize_connection_pool():
    """
    Initialize the connection pool. This should be called at application startup.
    """
    global connection_pool
    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    POSTGRES_DB = os.getenv('POSTGRES_DB')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')  # Default to localhost if not set
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', 5432)         # Default to 5432 if not set
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    connection_pool = await asyncpg.create_pool(DATABASE_URL)

async def get_pg_connection():
    """
    Get a connection from the connection pool.
    """
    global connection_pool
    if connection_pool is None:
        raise RuntimeError("Connection pool is not initialized. Call initialize_connection_pool() first.")
    
    return await connection_pool.acquire()

async def release_pg_connection(connection):
    """
    Release a connection back to the pool.
    """
    global connection_pool
    if connection_pool is None:
        raise RuntimeError("Connection pool is not initialized. Call initialize_connection_pool() first.")
    await connection_pool.release(connection)


# security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login/")

async def verify_token(request: Request, token: str = Depends(oauth2_scheme)):
    conn = await get_pg_connection()

    ip_check_query = "SELECT 1 FROM banned_ips WHERE ip = $1"
    ip_blocked = await conn.fetchval(ip_check_query, client_ip)
    if ip_blocked:
        raise HTTPException(status_code=403, detail="Your IP is blocked.")

    query = '''
        SELECT id 
        FROM users 
        WHERE token = $1 
    '''
    result = await conn.fetchrow(query, token)
    await release_pg_connection(conn)

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


def send_mail(receiver_email, subject, body):
    smtp_server = os.getenv('SMTP_HOST')
    smtp_port = os.getenv('SMTP_PORT') 
    sender_email = os.getenv('MAIL_ADDRESS') 
    sender_password = os.getenv('MAIL_PASSWORD') 

    # Create the email
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.set_content(body)

    # Send the email via SMTP over SSL
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


def send_fediverse(receiver, text):
    access_token = os.getenv('FEDIVERSE_ACCESS_TOKEN')
    url = os.getenv('FEDIVERSE_URL') 

    mastodon = Mastodon(
        access_token=access_token,
        api_base_url=url
    )

    message = f'{receiver} {text}'

    # Sende Toot mit Sichtbarkeit "direct"
    mastodon.status_post(
        message,
        visibility='direct'
    )


async def block_ip(ip : str):
    conn = await get_pg_connection()
    try:
        await conn.execute("INSERT INTO banned_ips (ip) VALUES ($1) ON CONFLICT (ip) DO NOTHING;", ip)
    except:
        pass
    finally:
        await release_pg_connection(conn)


async def unblock_ip(ip: str):
    conn = await get_pg_connection()
    try:
        await conn.execute("DELETE FROM banned_ips WHERE ip = $1;", ip)
    except Exception as e:
        pass
    finally:
        await release_pg_connection(conn)