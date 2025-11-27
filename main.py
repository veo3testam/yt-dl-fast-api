from flask import Flask, request, jsonify, send_file
import yt_dlp
import subprocess
import tempfile
import shutil
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "yt-dl-fast-api ready", "trim": True})

@app.route('/download')
def download_info():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing url"}), 400
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return jsonify({
            "title": info.get('title'),
            "duration": info.get('duration'),
            "thumbnail": info.get('thumbnail'),
            "stream_url": info['formats'][-1]['url'] if info['formats'] else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/trim', methods=['POST'])
def trim_video():
    data = request.json
    url = data.get('url')
    duration = data.get('duration', 59)
    start = data.get('start', 0)
    if not url:
        return jsonify({"error": "Missing url"}), 400
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_file = os.path.join(tmp_dir, 'trimmed.mp4')
        
        # yt-dlp DASH URLs only (no download)
        ydl_opts = {
            'format': 'bestvideo[height<=720]+bestaudio/best[height<=480]',
            'noplaylist': True, 'quiet': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            dash_url = info['url']  # Best DASH
            
            # FFmpeg trim stream direct
            cmd = [
                'ffmpeg', '-y', '-ss', str(start), '-t', str(duration),
                '-i', dash_url,
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '28',
                '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart',
                '-loglevel', 'error', output_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0 or os.path.getsize(output_file) == 0:
                return jsonify({"error": result.stderr}), 500
            
            return send_file(output_file, mimetype='video/mp4', as_attachment=True, download_name='trimmed.mp4')
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
