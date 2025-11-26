from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, StreamingResponse
import yt_dlp
import subprocess
import os
import tempfile
import shutil
from typing import Optional

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "yt-trim-59s server đang chạy khỏe – dùng /download hoặc /trim"}


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
            best_format = None
            for f in info.get("formats", []):
                if f.get("height", 0) <= 1080 and f.get("vcodec") != "none" and f.get("acodec") != "none":
                    if best_format is None or f.get("height", 0) > best_format.get("height", 0):
                        best_format = f

            if not best_format:
                best_format = info["url"] if "url" in info else info["formats"][-1]

            return JSONResponse({
                "title": info.get("title", "Unknown"),
                "description": info.get("description", ""),
                "uploader": info.get("uploader", "Unknown"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "streamUrl": best_format.get("url") if isinstance(best_format, dict) else best_format
            })
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/trim")
async def trim_video(url: str = Form(...), start: int = Form(0), duration: int = Form(59)):
    temp_dir = tempfile.mkdtemp()
    try:
        # Tải video về tạm (chỉ best 1080p hoặc thấp hơn)
        input_path = os.path.join(temp_dir, "input.mp4")
        subprocess.run([
            "yt-dlp", "-f", "best[height<=1080]/best", "--no-part", "-o", input_path, url
        ], check=True, capture_output=True)

        # Cắt 59s đầu tiên bằng ffmpeg (copy stream để nhanh + không re-encode)
        output_path = os.path.join(temp_dir, "trimmed_59s.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-ss", str(start), "-t", str(duration),
            "-c", "copy", "-avoid_negative_ts", "make_zero",
            output_path
        ], check=True, capture_output=True)

        # Stream file về client
        def iterfile():
            with open(output_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

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
