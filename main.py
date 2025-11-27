from fastapi import FastAPI, Form
from fastapi.responses import StreamingResponse, JSONResponse
import yt_dlp
import subprocess
import os
import tempfile
import shutil

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "yt-trim-59s running – ready to cut!"}

@app.get("/download")
async def download_metadata(url: str):
    ydl_opts = {"format": "best[height<=1080]/best", "quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get("url
            return {
                "title": info.get("title", "Unknown"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "streamUrl": stream_url
            }
        except:
            return JSONResponse({"error": "cannot get metadata"}, status_code=500)

@app.post("/trim")
async def trim_video(url: str = Form(...), start: int = Form(0), duration: int = Form(59)):
    temp_dir = tempfile.mkdtemp()
    input_file = os.path.join(temp_dir, "input.mp4")
    output_file = os.path.join(temp_dir, "output.mp4")

    try:
        # Bước 1: tải thẳng stream (không dùng -o để tránh lỗi format)
        subprocess.run([
            "yt-dlp", "-f", "best[height<=1080]/best", 
            "--no-part", "--merge-output-format", "mp4",
            "-o", input_file, url
        ], check=True, timeout=180)

        # Bước 2: cắt + remux chắc chắn có âm thanh + hình
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_file,
            "-ss", str(start),
            "-t", str(duration),
            "-c:v", "copy",
            "-c:a", "aac",
            "-avoid_negative_ts", "make_zero",
            output_file
        ], check=True, timeout=90)

        def file_generator():
            with open(output_file, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk

        return StreamingResponse(
            file_generator(),
            media_type="video/mp4",
            headers={"Content-Disposition": "attachment; filename=59s.mp4"}
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
