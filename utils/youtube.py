import logging
import os
import json
import yt_dlp
import requests
import subprocess
import shlex
import socket
from typing import Dict, List, Optional, Any
from urllib3.exceptions import ReadTimeoutError, ConnectTimeoutError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set a shorter timeout than Gunicorn's worker timeout (typically 30 seconds)
# This ensures our operations fail before Gunicorn kills the worker
YT_DLP_TIMEOUT = 15  # seconds for yt-dlp operations
SUBPROCESS_TIMEOUT = 15  # seconds for subprocess operations
REQUESTS_TIMEOUT = 8  # seconds for HTTP requests

def get_client_secrets_file() -> str:
    """Create and return path to client secrets file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    client_secrets_file = os.path.join(current_dir, 'client_secrets.json')
    
    # Create client_secrets.json if it doesn't exist
    if not os.path.exists(client_secrets_file):
        oauth_info = {
            "web": {
                "client_id": "1023316916513-0ceeamcb82h4c5j27p7pnrbq0fl9udhd.apps.googleusercontent.com",
                "project_id": "yt-metadata-442112",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": "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"
            }
        }
        with open(client_secrets_file, 'w') as f:
            json.dump(oauth_info, f)
        logger.info(f"Created client_secrets.json at {client_secrets_file}")
    
    return client_secrets_file

def fetch_proxies() -> List[str]:
    """Fetch proxy list from API endpoint."""
    try:
        response = requests.get("https://backendmix.vercel.app/ips", timeout=REQUESTS_TIMEOUT)
        if response.status_code == 200:
            proxy_data = response.json()
            proxies = proxy_data.get('proxies', [])
            logger.info(f"Fetched {len(proxies)} proxies")
            return proxies
        else:
            logger.warning(f"Failed to fetch proxies (status code: {response.status_code}), proceeding without proxies")
            return []
    except Exception as e:
        logger.warning(f"Error fetching proxies: {str(e)}")
        return []

def get_cookies_path() -> Optional[str]:
    """Get path to cookies file if it exists."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_path = os.path.join(current_dir, 'cookies.txt')
    if os.path.exists(cookies_path):
        logger.info(f"Found cookies file at {cookies_path}")
        return cookies_path
    logger.info("No cookies file found")
    return None

def extract_with_yt_dlp_api(url: str, proxy: Optional[str] = None, cookies_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract audio info using yt-dlp Python API."""
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': YT_DLP_TIMEOUT,  # Set a shorter timeout than Gunicorn's worker timeout
    }
    
    if proxy:
        ydl_opts['proxy'] = f"http://{proxy}"
    
    if cookies_path:
        ydl_opts['cookiefile'] = cookies_path
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'url': info['url'],
                'title': info['title'],
                'author': info.get('uploader', 'Unknown'),
                'thumbnail': info.get('thumbnail', '')
            }
    except (socket.timeout, ReadTimeoutError, ConnectTimeoutError) as e:
        # Convert socket timeouts to our own timeout exception
        logger.warning(f"Socket timeout with yt-dlp API: {str(e)}")
        raise requests.exceptions.Timeout(f"Socket timeout with yt-dlp API: {str(e)}")
    except Exception as e:
        # Re-raise any other exceptions
        raise

def extract_with_subprocess(url: str, proxy: Optional[str] = None, cookies_path: Optional[str] = None) -> Dict[str, Any]:
    """Extract audio info using yt-dlp via subprocess."""
    cmd_parts = ["yt-dlp"]
    
    if proxy:
        cmd_parts.extend(["--proxy", f"http://{proxy}"])
    
    if cookies_path:
        cmd_parts.extend(["--cookies", cookies_path])
    
    cmd_parts.extend([f"--socket-timeout", f"{YT_DLP_TIMEOUT}", "-f", "bestaudio", "--dump-json", url])
    
    # Convert command parts to a safe shell command string
    cmd = " ".join(shlex.quote(str(part)) for part in cmd_parts)
    logger.info(f"Running command: {cmd}")
    
    # Add timeout to subprocess call
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
        if result.stdout:
            info = json.loads(result.stdout)
            return {
                'url': info.get('url', ''),
                'title': info.get('title', ''),
                'author': info.get('uploader', 'Unknown'),
                'thumbnail': info.get('thumbnail', '')
            }
        raise Exception("Empty response from yt-dlp subprocess")
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Subprocess timeout: {str(e)}")
        raise

def extract_audio_url(url: str) -> Dict[str, Any]:
    """Extract audio stream URL from YouTube video using yt-dlp with proxy fallback."""
    # Prepare configurations
    get_client_secrets_file()
    proxies = fetch_proxies()
    cookies_path = get_cookies_path()
    
    # Try with each proxy
    if proxies:
        for proxy in proxies:
            # First try with Python API
            try:
                logger.info(f"Trying with proxy via Python API: {proxy}")
                return extract_with_yt_dlp_api(url, proxy, cookies_path)
            except (requests.exceptions.Timeout, ReadTimeoutError, ConnectTimeoutError, socket.timeout):
                logger.warning(f"Timeout with proxy {proxy} via Python API")
                continue  # Skip to next proxy on timeout
            except Exception as e:
                logger.warning(f"Failed with proxy {proxy} via Python API: {str(e)}")
                
                # If Python API fails with non-timeout error, try subprocess
                try:
                    logger.info(f"Trying with proxy via subprocess: {proxy}")
                    return extract_with_subprocess(url, proxy, cookies_path)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout with proxy {proxy} via subprocess")
                    continue  # Skip to next proxy on timeout
                except Exception as sub_e:
                    logger.warning(f"Failed with proxy {proxy} via subprocess: {str(sub_e)}")
                    continue
    
    # If all proxies fail or none available, try without proxy
    logger.info("All proxies failed or none available, trying without proxy")
    
    try:
        logger.info("Trying without proxy via Python API")
        return extract_with_yt_dlp_api(url, None, cookies_path)
    except Exception as e:
        logger.warning(f"Failed without proxy via Python API: {str(e)}")
        
        try:
            logger.info("Trying without proxy via subprocess")
            return extract_with_subprocess(url, None, cookies_path)
        except Exception as sub_e:
            error_msg = f"All extraction attempts failed: {str(sub_e)}"
            logger.error(error_msg)
            raise Exception(f"Failed to extract audio: {str(sub_e)}")

# Example usage
if __name__ == "__main__":
    try:
        result = extract_audio_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")
