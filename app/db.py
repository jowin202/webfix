import asyncpg
import os
from helper import calc_hmac




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






async def pg_db_init():
    conn = await get_pg_connection() 


    users_table = await conn.fetchval("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'users'
        )
    """)

    if users_table:
        await release_pg_connection(conn)
        return

    try:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS channels (
            id SERIAL PRIMARY KEY,
            name VARCHAR UNIQUE,
            visible BOOL DEFAULT true,
            owner INTEGER -- FK added later
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(20) UNIQUE NOT NULL,
                username_html VARCHAR,
                name VARCHAR(50),
                tel VARCHAR(20),
                mail VARCHAR(100),
                fediverse_id VARCHAR(100),
                login_msg VARCHAR DEFAULT 'has logged in.',
                logout_msg VARCHAR DEFAULT 'has logged out.',
                token VARCHAR(66),
                is_activated BOOL NOT NULL DEFAULT true,
                activation_token VARCHAR,
                lost_password_token VARCHAR,
                lost_password_token_valid_from TIMESTAMP,
                password VARCHAR NOT NULL,
                online_time INT DEFAULT 0,
                failed_attempts INT DEFAULT 0,
                created TIMESTAMP DEFAULT NOW(),
                last_posted TIMESTAMP,
                last_login TIMESTAMP,
                login_count INT DEFAULT 0,
                remove_on_logout BOOL DEFAULT false,
                visible BOOL DEFAULT true,
                admin INT NOT NULL DEFAULT 0,
                channel_id INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE RESTRICT
            )
        ''')


        await conn.execute('''
            ALTER TABLE channels
            ADD CONSTRAINT channels_owner_fkey FOREIGN KEY (owner) REFERENCES users(id) ON DELETE SET NULL
        ''')


        await conn.execute('''
            INSERT INTO channels (id,name) VALUES (1,'Main Channel')
            ON CONFLICT (name) DO NOTHING;
        ''')

        await conn.execute('''
            INSERT INTO channels (id,name) VALUES (2,'Secondary Channel')
            ON CONFLICT (name) DO NOTHING;
        ''')

        
        # Insert default admin user if not exists
        await conn.execute('''
            INSERT INTO users (username, username_html, name, tel, mail, token, password, admin) 
            VALUES ('admin', '<b>admin</b>', 'Administrator', '00000000', 'admin@admin.com', '', $1, 4)
            ON CONFLICT (username) DO NOTHING
        ''', calc_hmac(os.getenv("ADMIN_DEFAULT_PASSWORD")))



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


        await conn.execute('''
            CREATE TABLE IF NOT EXISTS private_messages (
            id SERIAL PRIMARY KEY,
            sender INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            receiver INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            sent_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        ''')


    except Exception as e:
        print(f"An error occurred: {e}",flush=True)
    finally:
        if conn:
            await release_pg_connection(conn)



async def pg_db_remove():
    conn = await get_pg_connection() 
    try:
        await conn.execute('''DROP TABLE users CASCADE''')
        await conn.execute('''DROP TABLE channels CASCADE''')
        await conn.execute('''DROP TABLE settings_str CASCADE''')
        await conn.execute('''DROP TABLE settings_bool CASCADE''')
        await conn.execute('''DROP TABLE settings_int CASCADE''')
        await conn.execute('''DROP TABLE banned_ips CASCADE''')
        await conn.execute('''DROP TABLE private_messages CASCADE''')

    except Exception as e:
        print(f"An error occurred: {e}",flush=True)
    finally:
        if conn:
            await release_pg_connection(conn)