import asyncpg
import os
from helper import get_pg_connection, release_pg_connection



async def pg_db_init():
    conn = None 
    try:
        conn = await get_pg_connection()

        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) UNIQUE,
                name VARCHAR(50),
                tel VARCHAR(20),
                mail VARCHAR(100),
                fediverse_id VARCHAR(100),
                token VARCHAR(66),
                mail_activate_token VARCHAR(66),
                lost_password_token VARCHAR(66),
                lost_password_token_valid_from TIMESTAMP,
                password VARCHAR(32),
                online_time INT DEFAULT 0,
                created TIMESTAMP DEFAULT NOW(),
                last_posted TIMESTAMP,
                last_login TIMESTAMP,
                admin INT NOT NULL DEFAULT 0 
            )
        ''')
        
        # Insert default admin user if not exists
        await conn.execute('''
            INSERT INTO users (username, name, tel, mail, token, password, admin) 
            VALUES ('admin', 'Administrator', '00000000', 'admin@admin.com', '', $1, 4)
            ON CONFLICT (username) DO NOTHING
        ''', os.getenv("ADMIN_DEFAULT_PASSWORD"))


        await conn.execute('''
            INSERT INTO users (username, name, tel, mail, fediverse_id, token, password) 
            VALUES ('johannes', 'Johannes Winkler', '00000000', 'johannes.w@gmx.at', '@jowin@pixelfed.graz.social', '', 'abc123')
            ON CONFLICT (username) DO NOTHING
        ''')





        # Create settings table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(20) UNIQUE,
                value_str VARCHAR(4096),
                value_int INT,
                value_bool BOOL
            )
        ''')

    except Exception as e:
        print(f"An error occurred: {e}",flush=True)
