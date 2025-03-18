import os
import logging
import platform
import socket
import requests
import subprocess
from flask import Flask, render_template, request, jsonify
from utils import validate_youtube_url, get_audio_stream

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/system-info')
def system_info():
    """Get system information, including IP and VPN status (admin use only)"""
    try:
        # Get IP address from external service
        external_ip = "Unknown"
        try:
            external_ip = requests.get('https://httpbin.org/ip', timeout=5).json()['origin']
        except Exception as e:
            external_ip = f"Error getting external IP: {str(e)}"

        # Get system information
        info = {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "external_ip": external_ip,
            "environment": "Production" if os.environ.get("RENDER") else "Development"
        }
        
        # Check for OpenVPN process
        vpn_status = "Not running"
        if platform.system() != "Windows":  # Skip on Windows
            try:
                result = subprocess.run(["pgrep", "openvpn"], capture_output=True, text=True)
                vpn_status = "Running" if result.stdout.strip() else "Not running"
            except Exception as e:
                vpn_status = f"Error checking VPN status: {str(e)}"
        
        info["vpn_status"] = vpn_status
        
        # Try a geo-location check to verify IP location
        try:
            geo_response = requests.get('https://ipinfo.io', timeout=5).json()
            info["ip_country"] = geo_response.get('country', 'Unknown')
            info["ip_region"] = geo_response.get('region', 'Unknown')
            info["ip_city"] = geo_response.get('city', 'Unknown')
        except Exception as e:
            info["geo_error"] = str(e)
        
        return jsonify(info)
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/play', methods=['POST'])
def play_audio():
    url = request.form.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    if not validate_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    try:
        # Log the request with detailed information
        logger.info(f"Processing YouTube URL: {url}")
        
        # Check VPN status if in production
        if os.environ.get("RENDER"):
            try:
                result = subprocess.run(["pgrep", "openvpn"], capture_output=True, text=True)
                vpn_running = bool(result.stdout.strip())
                logger.info(f"VPN status before extraction: {'Running' if vpn_running else 'Not running'}")
            except Exception as e:
                logger.warning(f"Could not check VPN status: {str(e)}")
        
        # Get direct stream URL
        stream_url, title = get_audio_stream(url)
        
        if not stream_url:
            raise ValueError("Failed to obtain audio stream URL")
            
        logger.info(f"Successfully obtained stream for '{title}'")
        return jsonify({
            'audio_path': stream_url,
            'title': title
        })

    except Exception as e:
        logger.error(f"Error processing URL {url}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Simple health check endpoint for Render"""
    try:
        # Verify VPN connectivity if running in production
        vpn_status = "Not applicable"
        if os.environ.get("RENDER"):
            try:
                result = subprocess.run(["pgrep", "openvpn"], capture_output=True, text=True)
                vpn_status = "Running" if result.stdout.strip() else "Not running"
            except Exception:
                vpn_status = "Error checking"
        
        return jsonify({
            "status": "healthy",
            "vpn": vpn_status
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return render_template('error.html', error="Internal server error"), 500

@app.after_request
def add_header(response):
    """Add headers to prevent caching for dynamic content"""
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response