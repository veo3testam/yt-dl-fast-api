from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import JSONResponse
import subprocess
import shutil
import os

app = FastAPI()

@app.get("/health")
async def health():
    # Check ffmpeg
    ffmpeg = shutil.which("ffmpeg")
    # Check yt-dlp
    ytdlp = shutil.which("yt-dlp") or shutil.which("yt-dlp")
    
    return {
        "status": "healthy" if ffmpeg and ytdlp else "degraded",
        "ffmpeg": ffmpeg or "NOT FOUND",
        "yt_dlp": ytdlp or "NOT FOUND",
        "uptime": "OK"
    }
