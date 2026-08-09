from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import asyncio
import os
import tempfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

def get_cookie_file(cookies_content):
    if not cookies_content:
        return None
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    tmp.write(cookies_content)
    tmp.flush()
    tmp.close()
    return tmp.name

@app.get("/stream/{video_id}")
async def get_stream(video_id: str):
    if not video_id or len(video_id) != 11:
        raise HTTPException(status_code=400, detail="Invalid video ID")

    cookies_content = os.environ.get("YT_COOKIES")
    cookie_file = get_cookie_file(cookies_content)

    # Try multiple player clients until one works
    clients = ["ios", "web", "android_vr", "tv_embedded"]

    try:
        for client in clients:
            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": [client],
                    }
                },
            }
            if cookie_file:
                ydl_opts["cookiefile"] = cookie_file

            try:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda o=ydl_opts: _extract(video_id, o))
                url = info.get("url")
                if url:
                    return {
                        "url": url,
                        "title": info.get("title"),
                        "duration": info.get("duration"),
                        "client": client,
                    }
            except Exception:
                continue

        raise HTTPException(status_code=502, detail="No client could get a stream URL")

    finally:
        if cookie_file:
            os.unlink(cookie_file)

@app.get("/debug/{video_id}")
async def debug_formats(video_id: str):
    """Returns all available formats so we can see what clients provide."""
    cookies_content = os.environ.get("YT_COOKIES")
    cookie_file = get_cookie_file(cookies_content)
    results = {}

    try:
        for client in ["ios", "web", "android", "android_vr", "tv_embedded"]:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "extractor_args": {"youtube": {"player_client": [client]}},
            }
            if cookie_file:
                ydl_opts["cookiefile"] = cookie_file
            try:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda o=ydl_opts: _extract(video_id, o))
                formats = [
                    {"id": f.get("format_id"), "ext": f.get("ext"), "acodec": f.get("acodec"), "vcodec": f.get("vcodec"), "abr": f.get("abr")}
                    for f in (info.get("formats") or [])
                ]
                results[client] = {"ok": True, "format_count": len(formats), "formats": formats}
            except Exception as e:
                results[client] = {"ok": False, "error": str(e)}
    finally:
        if cookie_file:
            os.unlink(cookie_file)

    return results

def _extract(video_id, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}",
            download=False
        )

@app.get("/health")
def health():
    return {"ok": True}
