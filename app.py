import os
import logging
import re
import requests
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from utils.youtube import extract_audio_url

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

def is_valid_youtube_url(url):
    """Validate YouTube URL format"""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    match = re.match(youtube_regex, url)
    return bool(match)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    youtube_url = request.form.get('url', '')
    if not youtube_url:
        return jsonify({"error": "Please enter a YouTube URL"}), 400
    if not is_valid_youtube_url(youtube_url):
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    try:
        audio_data = extract_audio_url(youtube_url)
        # Optionally modify the URL to use the proxy if needed
        if audio_data and 'url' in audio_data:
            # Store original URL
            audio_data['original_url'] = audio_data['url']
            # Create proxy URL (uncomment if you want automatic proxy redirection)
            # audio_data['url'] = f"/proxy/{audio_data['url']}"
        return jsonify(audio_data)
    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/proxy/<path:audio_url>', methods=['GET'])
def proxy_audio(audio_url):
    """
    Proxy endpoint that fetches the audio stream from the provided URL
    and forwards it to the client using the server's IP address.
    
    Usage: /proxy/https://example.com/audio-stream.mp3
    """
    try:
        # Log the proxy request
        logger.info(f"Proxying request for: {audio_url}")
        
        # Set up headers to forward to the target server
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.youtube.com/',
            'Origin': 'https://www.youtube.com'
        }
        
        # Get the range header if present (important for streaming)
        range_header = request.headers.get('Range')
        if range_header:
            headers['Range'] = range_header
        
        # Make the request to the actual media URL
        req = requests.get(
            audio_url,
            headers=headers,
            stream=True,
            timeout=15
        )
        
        # Prepare response headers
        response_headers = {
            'Content-Type': req.headers.get('Content-Type', 'application/octet-stream'),
            'Content-Length': req.headers.get('Content-Length', ''),
            'Accept-Ranges': req.headers.get('Accept-Ranges', 'bytes'),
        }
        
        # Add Content-Range header if it exists in the response
        if 'Content-Range' in req.headers:
            response_headers['Content-Range'] = req.headers['Content-Range']
        
        # Stream the response back to the client
        return Response(
            stream_with_context(req.iter_content(chunk_size=8192)),
            status=req.status_code,
            headers=response_headers
        )
        
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}")
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html'), 500
