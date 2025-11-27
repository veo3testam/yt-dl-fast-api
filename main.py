from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, StreamingResponse
import yt_dlp
import subprocess
import os
import tempfile
import shutil

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "yt-trim-59s server đang chạy khỏe!"}

@app.get("/download")
async def download_metadata(url: str):
    ydl_opts = {
        "format": "best[height<=1080]/best",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            best = None
            for f in formats:
                h = f.get("height") or 0
                if h <= 1080 and f.get("vcodec") != "none" and f.get("acodec") != "none":
                    if best is None or h > (best.get("height") or 0):
                        best = f
            if not best and formats:
                best = formats[-1]

            stream_url = best.get("url") if best else info.get("url")

            return JSONResponse({
                "title": info.get("title", "Unknown"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "streamUrl": stream_url
            })
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/trim")
async def trim_video(url: str = Form(...), start: int = Form(0), duration: int = Form(59)):
    temp_dir = tempfile.mkdtemp()
    try:
        input_path = os.path.join(temp_dir, "input.mp4")
        subprocess.run([
            "yt-dlp", "-f", "best[height<=1080]/best", "--no-part", "-o", input_path, url
        ], check=True, capture_output=True)

        output_path = os.path.join(temp_dir, "59s.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-ss", str(start), "-t", str(duration),
            "-c", "copy", "-avoid_negative_ts", "make_zero",
            output_path
        ], check=True, capture_output=True)

        def iterfile():
            with open(output_path, "rb") as f:
                yield from iter(lambda: f.read(8192), b"")

        return StreamingResponse(
            iterfile(),
            media_type="video/mp4",
            headers={"Content-Disposition": "attachment; filename=59s.mp4"}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
