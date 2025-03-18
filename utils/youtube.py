import os
import json
import logging
import yt_dlp
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video using yt-dlp with OAuth authentication and geo-location bypass for India"""
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
        
        # Multiple Indian IP addresses to try if one fails
        indian_ips = [
            '103.31.38.0',  # Mumbai
            '125.19.52.0',   # Delhi
            '202.53.92.0',   # Bangalore
            '117.197.40.0'   # Chennai
        ]
        
        # Headers that help bypass geo-restrictions
        headers = {
            'Accept-Language': 'hi-IN,hi;q=0.9,en-IN;q=0.8,en;q=0.7',
            'X-Forwarded-For': indian_ips[0],
            'CF-IPCountry': 'IN'
        }
        
        # Configure yt-dlp options with enhanced geo-location settings
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'client_secrets': client_secrets_file,
            'geo_bypass_country': 'IN',  # Set geo-location to India
            'geo_bypass': True,
            'http_headers': headers,
            'socket_timeout': 15,
            'retries': 5
        }
        
        # Fallback to cookies if available
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        if os.path.exists(cookies_path):
            logger.info(f"Found cookies file, using as fallback: {cookies_path}")
            ydl_opts['cookiefile'] = cookies_path
        
        # Try with the first configuration
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Attempting to extract info with primary settings")
                info = ydl.extract_info(url, download=False)
                logger.info(f"Successfully extracted info for {url}")
                return {
                    'url': info['url'],
                    'title': info['title'],
                    'author': info['uploader'],
                    'thumbnail': info['thumbnail']
                }
        except Exception as first_error:
            logger.warning(f"First extraction attempt failed: {str(first_error)}")
            
            # Try alternate IPs if the first one fails
            success = False
            for ip in indian_ips[1:]:
                try:
                    logger.info(f"Retrying with alternate Indian IP: {ip}")
                    ydl_opts['http_headers']['X-Forwarded-For'] = ip
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        logger.info(f"Successfully extracted info using IP {ip}")
                        success = True
                        return {
                            'url': info['url'],
                            'title': info['title'],
                            'author': info['uploader'],
                            'thumbnail': info['thumbnail']
                        }
                except Exception as retry_error:
                    logger.warning(f"Extraction with IP {ip} failed: {str(retry_error)}")
                    continue
            
            if not success:
                logger.error("All extraction attempts failed")
                raise Exception("Failed to extract audio after trying multiple Indian IPs")
    
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
