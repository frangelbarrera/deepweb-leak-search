import os
import asyncpg
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("deeptrawl.db")

DB_POOL = None
DATABASE_URL = os.getenv("DATABASE_URL", "postgres://deeptrawl:deeptrawl_pass@localhost:5432/deeptrawl_db")

SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS threat_intel (
        id SERIAL PRIMARY KEY,
        source VARCHAR(255) NOT NULL,
        type VARCHAR(50) NOT NULL,
        ioc TEXT NOT NULL,
        ioc_hash VARCHAR(64) NOT NULL UNIQUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_ioc_hash ON threat_intel(ioc_hash);
    CREATE INDEX IF NOT EXISTS idx_ioc_type_search ON threat_intel(type);
    CREATE INDEX IF NOT EXISTS idx_created_at_time ON threat_intel(created_at);

    CREATE TABLE IF NOT EXISTS feeds (
        id SERIAL PRIMARY KEY,
        url VARCHAR(255) NOT NULL UNIQUE,
        active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
"""

DEFAULT_FEEDS = [
    "https://openphish.com/feed.txt",
    "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset",
]


async def init_db():
    global DB_POOL
    try:
        DB_POOL = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
        async with DB_POOL.acquire() as conn:
            await conn.execute(SCHEMA_SQL)
            for feed_url in DEFAULT_FEEDS:
                await conn.execute(
                    "INSERT INTO feeds (url) VALUES ($1) ON CONFLICT (url) DO NOTHING",
                    feed_url,
                )
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
        raise


async def close_db():
    global DB_POOL
    if DB_POOL:
        await DB_POOL.close()
        logger.info("Database connection pool closed")


def get_pool():
    return DB_POOL
