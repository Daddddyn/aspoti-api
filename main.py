from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/stream/{video_id}")
async def get_stream(video_id: str):
    if not video_id or len(video_id) != 11:
        raise HTTPException(status_code=400, detail="Invalid video ID")

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: _extract(video_id, ydl_opts))
        url = info.get("url")
        if not url:
            raise HTTPException(status_code=502, detail="No stream URL found")
        return {"url": url, "title": info.get("title"), "duration": info.get("duration")}
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=502, detail=str(e))

def _extract(video_id, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

@app.get("/health")
def health():
    return {"ok": True}
