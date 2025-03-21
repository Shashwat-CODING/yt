import logging
import os
import json
import yt_dlp
import subprocess
import shlex
import time
import signal
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    """Context manager to limit execution time of a block"""
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def extract_audio_url(url, max_timeout=30):
    """Extract audio stream URL from YouTube video using yt-dlp"""
    try:
        # Define the path to the client secrets file relative to this script
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
        
        # Check if cookies file exists
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        cookies_arg = f"--cookies {shlex.quote(cookies_path)}" if os.path.exists(cookies_path) else ""
        logger.info(f"Cookies path: {cookies_path}, exists: {os.path.exists(cookies_path)}")
        
        # Direct connection options
        ydl_opts = {
            'format': 'bestaudio',
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': max_timeout,
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        }
        
        if os.path.exists(cookies_path):
            ydl_opts['cookiefile'] = cookies_path
        
        logger.info("Extracting audio URL with direct connection")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logger.info("Successfully extracted with direct connection")
                return {
                    'url': info['url'],
                    'title': info['title'],
                    'author': info['uploader'],
                    'thumbnail': info['thumbnail']
                }
        except Exception as e:
            logger.warning(f"Direct connection failed: {str(e)}")
            
            # Fallback: Try subprocess method
            try:
                cmd = f"yt-dlp --socket-timeout {max_timeout} {cookies_arg} -f bestaudio --dump-json {shlex.quote(url)}"
                logger.info(f"Running subprocess: {cmd}")
                
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=max_timeout+2)
                if result.stdout:
                    info = json.loads(result.stdout)
                    logger.info("Successfully extracted with subprocess")
                    return {
                        'url': info.get('url', ''),
                        'title': info.get('title', ''),
                        'author': info.get('uploader', ''),
                        'thumbnail': info.get('thumbnail', '')
                    }
            except Exception as sub_e:
                logger.error(f"Subprocess attempt failed: {str(sub_e)}")
                raise Exception(f"All extraction methods failed. Last error: {str(sub_e)}")
            
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
