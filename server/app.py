import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI

from fetchers import fetch_instagram, fetch_tiktok, result_to_dict

load_dotenv()

TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME", "")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

_cache: Optional[Dict[str, Any]] = None
_cache_time: float = 0.0


def _is_stale() -> bool:
    return _cache is None or (time.time() - _cache_time) > CACHE_TTL_SECONDS


def _refresh_counts() -> Dict[str, Any]:
    global _cache, _cache_time

    results = []

    if TIKTOK_USERNAME:
        results.append(fetch_tiktok(TIKTOK_USERNAME))
    if INSTAGRAM_USERNAME:
        results.append(fetch_instagram(INSTAGRAM_USERNAME))

    _cache = {
        "updated_at": int(time.time()),
        "platforms": [result_to_dict(r) for r in results],
    }
    _cache_time = time.time()
    return _cache


@asynccontextmanager
async def lifespan(_: FastAPI):
    if any([TIKTOK_USERNAME, INSTAGRAM_USERNAME]):
        _refresh_counts()
    yield


app = FastAPI(title="Sub Count API", lifespan=lifespan)


@app.get("/")
def health():
    return {"status": "ok"}


@app.get("/counts")
def get_counts(force: bool = False):
    if force or _is_stale():
        _refresh_counts()
    return _cache or {"updated_at": None, "platforms": []}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("app:app", host=host, port=port, reload=True)
