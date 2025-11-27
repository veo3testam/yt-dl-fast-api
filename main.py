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
    return {"status": "yt-trim-59s v9 – running perfectly"}

@app.get("/download")
async def download_metadata(url: str):
    ydl_opts = {"format": "best[height<=1080]/best", "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            # Lấy link stream tốt nhất ≤1080p có cả hình + tiếng
            best_format = None
            for f in info.get("formats", []):
                if f.get("height", 0) <= 1080 and f.get("vcodec") != "none" and f.get("acodec") != "none":
                    if not best_format or f.get("height", 0) > best_format.get("height", 0):
                        best_format = f
            if not best_format:
                best_format = info["formats"][-1]

            return JSONResponse({
                "title": info.get("title", "Unknown"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "streamUrl": best_format.get("url")
            })
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/trim")
async def trim_video(url: str = Form(...), start: int = Form(0), duration: int = Form(59)):
    temp_dir = tempfile.mkdtemp()
    input_file = os.path.join(temp_dir, "input.mp4")
    output_file = os.path.join(temp_dir, "59s.mp4")

    try:
        # Bước 1: tải video chất lượng cao nhất ≤1080p
        subprocess.run([
            "yt-dlp", "-f", "best[height<=1080]/best", 
            "--merge-output-format", "mp4",
            "--no-part", "-o", input_file, url
        ], check=True, timeout=180, capture_output=True)

        # Bước 2: cắt + remux chắc chắn có âm thanh
        subprocess.run([
            "ffmpeg", "-y", "-i", input_file,
            "-ss", str(start), "-t", str(duration),
            "-c:v", "copy", "-c:a", "aac",
            "-movflags", "+faststart",
            output_file
        ], check=True, timeout=90, capture_output=True)

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
