from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
import yt_dlp
import subprocess
import tempfile
import shutil
import os
from typing import Optional

app = FastAPI()

@app.get("/")
def root():
    return {"status": "yt-dl-fast-api DASH trim ready"}

@app.get("/download")
def download(url: str):
    ydl_opts = {'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {
            "title": info.get('title'),
            "duration": info.get('duration'),
            "thumbnail": info.get('thumbnail'),
            "dash_url": [f['url'] for f in info['formats'] if f.get('protocol') == 'm3u8_dash'][-1] if info['formats'] else None
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/trim")
def trim(request: Request):
    data = request.json()
    url = data.get("url")
    duration: Optional[int] = data.get("duration", 59)
    start: Optional[int] = data.get("start", 0)
    if not url:
        return {"error": "Missing url"}

    tmp_dir = tempfile.mkdtemp()
    output_file = os.path.join(tmp_dir, "trimmed.mp4")
    
    try:
        # DASH URL only
        ydl_opts = {'format': 'bestvideo[height<=720]+bestaudio/best[height<=480]', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            dash_url = info['url']
        
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-t", str(duration),
            "-i", dash_url, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-loglevel", "error",
            output_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0 or not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            shutil.rmtree(tmp_dir)
            return {"error": result.stderr or "FFmpeg fail"}
        
        return FileResponse(output_file, media_type="video/mp4", filename="trimmed.mp4")
    finally:
        shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
