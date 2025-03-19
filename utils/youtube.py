import logging
import os
import json
import yt_dlp
import requests

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
        
        # Base yt-dlp options
        base_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'client_secrets': client_secrets_file,
            'geo_bypass_country': 'IN',  # Set geo-location to India
            'geo_bypass': True,
        }
        
        # Fallback to cookies if available
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        if os.path.exists(cookies_path):
            logger.info(f"Found cookies file, using as fallback: {cookies_path}")
            base_opts['cookiefile'] = cookies_path
        
        # Try with each proxy
        last_error = None
        for proxy in proxies:
            try:
                ydl_opts = base_opts.copy()
                ydl_opts['geo_verification_proxy'] = proxy
                logger.info(f"Trying with proxy: {proxy}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"Successfully extracted with proxy: {proxy}")
                    return {
                        'url': info['url'],
                        'title': info['title'],
                        'author': info['uploader'],
                        'thumbnail': info['thumbnail']
                    }
            except Exception as e:
                last_error = e
                logger.warning(f"Failed with proxy {proxy}: {str(e)}")
                continue
        
        # If all proxies fail, try without proxy
        logger.info("All proxies failed or none available, trying without proxy")
        ydl_opts = base_opts.copy()
        ydl_opts['geo_verification_proxy'] = ''  # Empty string for auto-detect
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'url': info['url'],
                'title': info['title'],
                'author': info['uploader'],
                'thumbnail': info['thumbnail']
            }
            
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
