import asyncpg
import os
from helper import get_pg_connection, release_pg_connection, calc_hmac



async def pg_db_init():
    conn = None 
    try:
        conn = await get_pg_connection()

        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) UNIQUE NOT NULL,
                username_html VARCHAR GENERATED ALWAYS AS ('<b>' || username || '</b>') STORED,
                name VARCHAR(50),
                tel VARCHAR(20),
                mail VARCHAR(100),
                fediverse_id VARCHAR(100),
                token VARCHAR(66),
                is_activated BOOL NOT NULL DEFAULT true,
                activation_token VARCHAR,
                lost_password_token VARCHAR,
                lost_password_token_valid_from TIMESTAMP,
                password VARCHAR NOT NULL,
                online_time INT DEFAULT 0,
                created TIMESTAMP DEFAULT NOW(),
                last_posted TIMESTAMP,
                last_login TIMESTAMP,
                login_count INT DEFAULT 0,
                remove_on_logout BOOL DEFAULT false,
                visible BOOL DEFAULT true,
                admin INT NOT NULL DEFAULT 0 
            )
        ''')
        
        # Insert default admin user if not exists
        await conn.execute('''
            INSERT INTO users (username, name, tel, mail, token, password, admin) 
            VALUES ('admin', 'Administrator', '00000000', 'admin@admin.com', '', $1, 4)
            ON CONFLICT (username) DO NOTHING
        ''', calc_hmac(os.getenv("ADMIN_DEFAULT_PASSWORD")))


        #await conn.execute('''
        #    INSERT INTO users (username, name, tel, mail, fediverse_id, token, password) 
        #    VALUES ('johannes', 'Johannes Winkler', '00000000', 'johannes.w@gmx.at', '@jowin@pixelfed.graz.social', '', 'abc123')
        #    ON CONFLICT (username) DO NOTHING
        #''')





        # Create settings table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS settings_str (
                key VARCHAR UNIQUE,
                value_str VARCHAR
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS settings_bool (
                key VARCHAR UNIQUE,
                value_bool BOOL
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS settings_int (
                key VARCHAR UNIQUE,
                value_int INT
            )
        ''')


        await conn.execute('''
            CREATE TABLE IF NOT EXISTS banned_ips (
            id SERIAL PRIMARY KEY,
            ip INET NOT NULL,
            time TIMESTAMP DEFAULT NOW()
            )
        ''')

    except Exception as e:
        print(f"An error occurred: {e}",flush=True)
