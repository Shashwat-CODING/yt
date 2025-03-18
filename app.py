import os
import logging
import re
import requests
from urllib.parse import unquote, quote
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
        # Add a proxied URL to the response
        if audio_data and 'url' in audio_data:
            audio_data['original_url'] = audio_data['url']
            audio_data['proxied_url'] = f"/proxy?url={quote(audio_data['url'])}"
        return jsonify(audio_data)
    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/proxy', methods=['GET'])
def proxy_audio():
    """
    Enhanced proxy endpoint that handles YouTube stream URLs properly
    by mimicking a real browser request.
    """
    try:
        # Get URL from query parameter
        audio_url = request.args.get('url')
        if not audio_url:
            return jsonify({"error": "Missing URL parameter"}), 400
        
        # Ensure URL is properly decoded
        audio_url = unquote(audio_url)
        
        logger.info(f"Proxying request for: {audio_url}")
        
        # Create session to maintain cookies
        session = requests.Session()
        
        # Comprehensive browser-like headers
        browser_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://www.youtube.com',
            'Referer': 'https://www.youtube.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Ch-Ua': '"Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Connection': 'keep-alive',
            'DNT': '1',
        }
        
        # Forward original request range if present
        if 'Range' in request.headers:
            browser_headers['Range'] = request.headers['Range']
        
        # Send HEAD request first to check if URL is valid and get headers
        try:
            head_response = session.head(
                audio_url, 
                headers=browser_headers, 
                timeout=10,
                allow_redirects=True
            )
            
            if head_response.status_code >= 400:
                logger.warning(f"HEAD request failed with status {head_response.status_code}")
        except Exception as e:
            logger.warning(f"HEAD request failed: {str(e)}")
        
        # Now make the actual GET request
        req = session.get(
            audio_url,
            headers=browser_headers,
            stream=True,
            timeout=20,
            allow_redirects=True
        )
        
        # If we still get a 403, try alternative approach
        if req.status_code == 403:
            logger.warning("Received 403, trying alternative approach...")
            
            # Try with different headers
            alt_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
                'Accept': '*/*',
                'Accept-Encoding': 'identity;q=1, *;q=0',
                'Accept-Language': 'en-US;q=0.9,en;q=0.8',
                'Range': 'bytes=0-',
            }
            
            if 'Range' in request.headers:
                alt_headers['Range'] = request.headers['Range']
            
            req = session.get(
                audio_url,
                headers=alt_headers,
                stream=True,
                timeout=20,
                allow_redirects=True
            )
        
        # If still failing, log helpful information
        if req.status_code >= 400:
            logger.error(f"Request failed with status {req.status_code}: {req.text[:200]}...")
            return jsonify({
                "error": f"Proxy request failed with status {req.status_code}",
                "url": audio_url,
                "response": req.text[:200] + "..."
            }), req.status_code
        
        # Copy relevant headers from the response
        response_headers = {}
        important_headers = [
            'Content-Type', 'Content-Length', 'Accept-Ranges',
            'Content-Range', 'Content-Encoding', 'Connection',
            'Cache-Control', 'Expires'
        ]
        
        for header in important_headers:
            if header in req.headers:
                response_headers[header] = req.headers[header]
        
        # Ensure content-type exists
        if 'Content-Type' not in response_headers:
            response_headers['Content-Type'] = 'audio/webm'
        
        # Stream the response back to the client
        return Response(
            stream_with_context(req.iter_content(chunk_size=8192)),
            status=req.status_code,
            headers=response_headers
        )
        
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}")
        return jsonify({
            "error": f"Proxy error: {str(e)}",
            "url": audio_url if 'audio_url' in locals() else "URL not processed yet"
        }), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('index.html'), 500
