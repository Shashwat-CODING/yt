import logging
import os
import json
import yt_dlp
import requests
import subprocess
import shlex

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video using yt-dlp with OAuth authentication and geo-location"""
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
        
        # Get proxies from the dynamic JSON
        try:
            response = requests.get("https://raw.githubusercontent.com/Shashwat-CODING/yt/refs/heads/main/wpr.json")
            if response.status_code == 200:
                proxy_data = response.json()
                proxies = proxy_data.get('proxies', [])
                logger.info(f"Fetched {len(proxies)} proxies")
            else:
                proxies = []
                logger.warning("Failed to fetch proxies, proceeding without proxies")
        except Exception as e:
            proxies = []
            logger.warning(f"Error fetching proxies: {str(e)}")
        
        # Check if cookies file exists
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        cookies_arg = f"--cookies {shlex.quote(cookies_path)}" if os.path.exists(cookies_path) else ""
        logger.info(f"Cookies path: {cookies_path}, exists: {os.path.exists(cookies_path)}")
        
        # Try each proxy using the exact command-line approach that works
        last_error = None
        for proxy in proxies:
            try:
                proxy_url = f"http://{proxy}"
                
                # First attempt: Use yt-dlp Python API with exact same parameters
                logger.info(f"Trying with proxy via Python API: {proxy_url}")
                ydl_opts = {
                    'format': 'bestaudio',
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'proxy': proxy_url,
                }
                
                if os.path.exists(cookies_path):
                    ydl_opts['cookiefile'] = cookies_path
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"Successfully extracted with proxy: {proxy_url}")
                    return {
                        'url': info['url'],
                        'title': info['title'],
                        'author': info['uploader'],
                        'thumbnail': info['thumbnail']
                    }
            except Exception as e:
                # If Python API fails, try subprocess approach (exactly matching your working command)
                logger.warning(f"Failed with proxy {proxy} via Python API: {str(e)}")
                try:
                    logger.info(f"Trying with proxy via subprocess: {proxy_url}")
                    cmd = f"yt-dlp --proxy {shlex.quote(proxy_url)} {cookies_arg} -f bestaudio --dump-json {shlex.quote(url)}"
                    logger.info(f"Running command: {cmd}")
                    
                    result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
                    if result.stdout:
                        info = json.loads(result.stdout)
                        logger.info(f"Successfully extracted with proxy via subprocess: {proxy_url}")
                        return {
                            'url': info.get('url', ''),
                            'title': info.get('title', ''),
                            'author': info.get('uploader', ''),
                            'thumbnail': info.get('thumbnail', '')
                        }
                except Exception as sub_e:
                    logger.warning(f"Failed with proxy {proxy} via subprocess: {str(sub_e)}")
                    last_error = sub_e
                    continue
        
        # If all proxies fail, try without proxy
        logger.info("All proxies failed or none available, trying without proxy")
        try:
            ydl_opts = {
                'format': 'bestaudio',
                'quiet': True,
                'no_warnings': True,
            }
            
            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'url': info['url'],
                    'title': info['title'],
                    'author': info['uploader'],
                    'thumbnail': info['thumbnail']
                }
        except Exception as e:
            # Final fallback: try subprocess without proxy
            logger.warning(f"Failed without proxy via Python API: {str(e)}")
            try:
                cmd = f"yt-dlp {cookies_arg} -f bestaudio --dump-json {shlex.quote(url)}"
                logger.info(f"Running final command without proxy: {cmd}")
                
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
                if result.stdout:
                    info = json.loads(result.stdout)
                    return {
                        'url': info.get('url', ''),
                        'title': info.get('title', ''),
                        'author': info.get('uploader', ''),
                        'thumbnail': info.get('thumbnail', '')
                    }
            except Exception as sub_e:
                logger.error(f"All extraction attempts failed: {str(sub_e)}")
                raise Exception(f"Failed to extract audio: {str(sub_e)}")
            
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
