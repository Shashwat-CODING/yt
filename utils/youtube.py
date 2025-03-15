import logging
import os
import json
import random
import yt_dlp

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video using yt-dlp with enhanced authentication and geo-bypass"""
    try:
        # Define paths relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        client_secrets_file = os.path.join(current_dir, 'client_secrets.json')
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        
        # Load client secrets to use as API key if available
        api_key = None
        if os.path.exists(client_secrets_file):
            try:
                with open(client_secrets_file, 'r') as f:
                    client_secrets = json.load(f)
                    if 'web' in client_secrets and 'client_id' in client_secrets['web']:
                        logger.info("Client secrets file found")
                        api_key = client_secrets['web'].get('api_key')
            except Exception as e:
                logger.warning(f"Error reading client_secrets.json: {str(e)}")
        
        # Random Indian IP to help with geo-bypass
        indian_ips = [
            "103.48.198.0", "122.176.32.0", "182.74.80.0", 
            "117.196.0.0", "14.139.45.0", "103.27.8.0"
        ]
        fake_ip = random.choice(indian_ips)
        
        # Base options for yt-dlp with enhanced geo-bypass
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'geo_bypass_country': 'IN',  # Set geo-location to India
            'geo_bypass': True,
            'geo_verification_proxy': f"{fake_ip}:80",
            'source_address': fake_ip,  # Bind to specific IP
            'referer': 'https://www.youtube.com/',  # Add referer
            'http_headers': {
                'X-Forwarded-For': fake_ip,
                'Accept-Language': 'en-IN,hi-IN;q=0.9,en;q=0.8,hi;q=0.7',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.youtube.com/',
                'Origin': 'https://www.youtube.com',
            }
        }
        
        # Add authentication methods in order of preference
        auth_method_used = "none"
        
        # 1. Try with cookies if available
        if os.path.exists(cookies_path):
            logger.info(f"Using cookies file for authentication: {cookies_path}")
            ydl_opts['cookiefile'] = cookies_path
            auth_method_used = "cookies"
        
        # 2. Add API key if available (as a backup)
        if api_key:
            logger.info("Using API key from client_secrets.json")
            ydl_opts['youtube_include_dash_manifest'] = False
            auth_method_used = f"{auth_method_used}+api_key"
            
        logger.info(f"Attempting extraction with auth method: {auth_method_used}")
        
        # First try with regular options
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logger.info(f"Successfully extracted audio URL using auth method: {auth_method_used}")
                return {
                    'url': info['url'],
                    'title': info['title'],
                    'author': info['uploader'],
                    'thumbnail': info['thumbnail'],
                    'auth_method': auth_method_used
                }
        except Exception as e:
            if "403" in str(e):
                # If we got a 403, try again with alternative options
                logger.warning(f"Got 403 error, trying alternative approach: {str(e)}")
                
                # Alternative approach - sometimes works for 403 errors
                alt_opts = ydl_opts.copy()
                alt_opts['format'] = 'bestaudio[acodec^=opus]/bestaudio/best'
                alt_opts['extractor_args'] = {'youtube': {'player_client': ['android']}}
                
                with yt_dlp.YoutubeDL(alt_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"Successfully extracted audio URL using alternative method")
                    return {
                        'url': info['url'],
                        'title': info['title'],
                        'author': info['uploader'],
                        'thumbnail': info['thumbnail'],
                        'auth_method': f"{auth_method_used}+alternative"
                    }
            else:
                # Re-raise other errors
                raise
                
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
