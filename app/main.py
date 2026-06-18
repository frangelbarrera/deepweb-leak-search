import asyncio
import hashlib
import logging
import re
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from pydantic import BaseModel, field_validator

from app.database import init_db, close_db, get_pool
from app.core.collector import fetch_all
from app.core.extractor import extract_iocs
from app.core.identity_manager import trigger_identity_renewal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("deeptrawl.api")

templates = Jinja2Templates(directory="app/templates")

# ---------------------------------------------------------------------------
# Background task: auto-collect every hour
# ---------------------------------------------------------------------------
async def auto_collect_task():
    while True:
        await asyncio.sleep(3600)
        try:
            await trigger_collection()
        except Exception as exc:
            logger.error("Scheduled collection failed: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(auto_collect_task())
    logger.info("DeepTrawl started — collection scheduled every 60 minutes")
    yield
    task.cancel()
    await close_db()


app = FastAPI(title="DeepTrawl — Deep Web Leak Search", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
URL_RE = re.compile(r"^https?://", re.IGNORECASE)

class FeedCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL must not be empty")
        if not URL_RE.match(v):
            raise ValueError("URL must start with http:// or https://")
        parsed = urlparse(v)
        if not parsed.netloc:
            raise ValueError("URL has no valid hostname")
        if len(v) > 2048:
            raise ValueError("URL exceeds 2048 characters")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/v1/health")
async def health_check():
    pool = get_pool()
    if not pool:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "detail": "Database not connected"})
    return {"status": "healthy"}


@app.get("/api/v1/feeds")
async def get_feeds():
    pool = get_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    async with pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM feeds ORDER BY created_at DESC")
        return {"feeds": [dict(r) for r in records]}


@app.post("/api/v1/feeds")
async def add_feed(feed: FeedCreate):
    pool = get_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO feeds (url) VALUES ($1) ON CONFLICT (url) DO NOTHING",
                feed.url,
            )
            logger.info("Feed added: %s", feed.url)
            return {"status": "success", "message": f"Feed added"}
        except Exception as exc:
            logger.error("Failed to add feed %s: %s", feed.url, exc)
            raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/network/rotate")
async def rotate_network_identity():
    success = await trigger_identity_renewal()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to renew Tor identity")
    return {"status": "success", "message": "Tor identity renewed"}


@app.post("/api/v1/trigger")
async def trigger_collection():
    pool = get_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        records = await conn.fetch("SELECT url FROM feeds WHERE active = TRUE")
        urls = [r["url"] for r in records]

    if not urls:
        return {"status": "success", "processed_iocs": 0, "message": "No active feeds"}

    logger.info("Starting collection from %d feed(s)", len(urls))
    responses = await fetch_all(urls)

    all_iocs = []
    for response in responses:
        if response.get("status") == 200 and response.get("content"):
            iocs = extract_iocs(response["content"])
            source = response.get("url", "unknown")
            for ioc in iocs:
                ioc_hash = hashlib.sha256(ioc["value"].encode()).hexdigest()
                all_iocs.append({
                    "source": source,
                    "type": ioc["type"],
                    "ioc": ioc["value"],
                    "ioc_hash": ioc_hash,
                })
        elif response.get("error"):
            logger.warning("Feed %s error: %s", response.get("url"), response["error"])

    inserted = 0
    if all_iocs:
        async with pool.acquire() as conn:
            records = [
                (ioc["source"], ioc["type"], ioc["ioc"], ioc["ioc_hash"])
                for ioc in all_iocs
            ]
            result = await conn.executemany(
                """
                INSERT INTO threat_intel (source, type, ioc, ioc_hash)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (ioc_hash) DO NOTHING
                """,
                records,
            )
            inserted = len(all_iocs)

    logger.info("Collection complete — %d IOCs processed", inserted)
    return {"status": "success", "processed_iocs": inserted}


@app.get("/api/v1/indicators")
async def get_indicators(limit: int = 50, page: int = 1, ioc_type: str = None):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")

    pool = get_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    offset = (page - 1) * limit
    where = ""
    params = []

    if ioc_type and ioc_type != "all":
        where = " WHERE type = $1"
        params.append(ioc_type)

    async with pool.acquire() as conn:
        records = await conn.fetch(
            f"SELECT id, source, type, ioc, ioc_hash, created_at FROM threat_intel{where} "
            f"ORDER BY created_at DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}",
            *params, limit, offset,
        )
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM threat_intel{where}",
            *params,
        )
        return {
            "total": total or 0,
            "page": page,
            "limit": limit,
            "indicators": [dict(r) for r in records],
        }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    pool = get_pool()
    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={"db_online": pool is not None}
    )
