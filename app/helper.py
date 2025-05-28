
import string
import random
import os

import smtplib
from email.message import EmailMessage

from datetime import datetime
from mastodon import Mastodon

import hmac
import hashlib
import base64



def token_generate():
    password = []
    characterList = ""
    characterList += string.ascii_letters
    characterList += string.digits
    for i in range(32):
        randomchar = random.choice(characterList)
        password.append(randomchar)
    return str("".join(password))





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





def calc_hmac(message: str) -> str:
    key_bytes = bytes.fromhex(os.getenv('HMAC_KEY'))
    message_bytes = message.encode('utf-8')
    hmac_result = hmac.new(key_bytes, message_bytes, hashlib.sha256).digest()
    
    return base64.b64encode(hmac_result).decode('utf-8')