# DeepTrawl

Deep web leak search. Aggregates Indicators of Compromise (IOCs) from public threat intelligence feeds, routing all traffic through Tor for anonymity. Built for security researchers and OSINT analysts.

![DeepTrawl Dashboard](assets/images/screenshot.png)

## What It Does

- Scrapes threat intelligence feeds (`.txt`, `.netset`) through Tor SOCKS5 proxies
- Extracts IOCs: IPv4, domains, emails, MD5, SHA256, BTC/XMR wallet addresses
- Stores results in PostgreSQL with SHA-256 deduplication
- Exposes a REST API + minimal dashboard
- Rotates Tor identity on demand or when rate-limited (via `stem` + Tor ControlPort)

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.11+, FastAPI, aiohttp |
| Proxy | Tor SOCKS5 (`aiohttp-socks`) |
| Identity rotation | `stem` + Tor ControlPort (`NEWNYM`) |
| Database | PostgreSQL 15 (`asyncpg`) |
| Extraction | Regex engine (deterministic, no ML) |
| UI | Jinja2 server-rendered dashboard |

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Or: Python 3.11+, PostgreSQL, and a running Tor daemon

### Docker (recommended)

```bash
docker compose up -d --build
```

Dashboard at `http://localhost:8000/dashboard`.

### Local (no Docker for app)

```bash
# 1. Start PostgreSQL + Tor
# 2. Install deps
pip install -r requirements.txt
# 3. Set env vars
export DATABASE_URL="postgres://user:pass@localhost:5432/dbname"
export UPSTREAM_PROXY="socks5h://127.0.0.1:9050"
export TOR_CONTROL_HOST="127.0.0.1"
export TOR_CONTROL_PORT="9051"
# 4. Run
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Database health check |
| GET | `/api/v1/feeds` | List active feed URLs |
| POST | `/api/v1/feeds` | Add a feed URL |
| POST | `/api/v1/trigger` | Force collection of all active feeds |
| POST | `/api/v1/network/rotate` | Renew Tor circuit |
| GET | `/api/v1/indicators` | Paginated IOCs (`?limit=50&page=1&ioc_type=ipv4`) |
| GET | `/dashboard` | Web dashboard |

## Default Feeds

- `https://openphish.com/feed.txt`
- `https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset`

Add or remove feeds via the API or dashboard.

## Project Structure

```
├── app/
│   ├── core/
│   │   ├── collector.py        # Async HTTP engine + Tor proxy
│   │   ├── extractor.py        # Regex IOC extraction
│   │   └── identity_manager.py # Tor identity rotation (NEWNYM)
│   ├── templates/
│   │   └── dashboard.html      # Jinja2 dashboard template
│   ├── database.py             # asyncpg connection pool + schema
│   └── main.py                 # FastAPI app + endpoints + auto-cron
├── src/                        # React landing page (Vite + Tailwind)
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── tests/
│   ├── test_extractor.py       # 26 tests — IOC regex extraction
│   └── test_api.py             # 11 tests — HTTP endpoints
├── assets/
│   └── images/
│       └── screenshot.png
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Limitations

- **Not a crawler** — only fetches plain-text feed URLs (no recursive spidering)
- **Regex-only extraction** — no NLP or fuzzy matching; IPv4 pattern matches any `X.X.X.X` without octet-range validation
- **No authentication** on the dashboard/API (local tool by design)
- **No persistent Tor identity tracking** — no circuit isolation per feed
- The `src/` React frontend is a separate landing page and not wired to the backend API directly

## License

MIT
