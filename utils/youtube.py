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
        
        # Random proxies to help with geo-bypass (optional)
        indian_ips = [
            "103.48.198.0", "122.176.32.0", "182.74.80.0", 
            "117.196.0.0", "14.139.45.0", "103.27.8.0"
        ]
        fake_ip = random.choice(indian_ips)
        
        # Base options for yt-dlp with different player clients and formats
        ydl_opts = {
            'format': 'bestaudio',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'geo_bypass': True,
            'geo_bypass_country': 'US',  # Try US first
            'http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.youtube.com/',
                'Origin': 'https://www.youtube.com',
            },
            # Use multiple extractors in sequence
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android', 'ios'],  # Try multiple clients
                    'player_skip': ['webpage', 'configs', 'js']  # Skip some potentially problematic extractions
                }
            }
        }
        
        # Add authentication methods
        if os.path.exists(cookies_path):
            logger.info(f"Using cookies file for authentication: {cookies_path}")
            ydl_opts['cookiefile'] = cookies_path
            auth_method_used = "cookies"
        else:
            auth_method_used = "none"
        
        # Try extraction methods in sequence
        extraction_methods = [
            # Method 1: Web client with default settings
            ydl_opts,
            
            # Method 2: Android client
            {**ydl_opts, 
             'format': 'bestaudio[acodec^=opus]/bestaudio/best',
             'extractor_args': {'youtube': {'player_client': ['android']}}
            },
            
            # Method 3: iOS client
            {**ydl_opts, 
             'format': 'bestaudio[acodec^=opus]/bestaudio/best',
             'extractor_args': {'youtube': {'player_client': ['ios']}}
            },
            
            # Method 4: With geo-bypass to India
            {**ydl_opts, 
             'geo_bypass_country': 'IN',
             'http_headers': {**ydl_opts['http_headers'], 'X-Forwarded-For': fake_ip,
                             'Accept-Language': 'en-IN,hi-IN;q=0.9,en;q=0.8,hi;q=0.7'}
            },
            
            # Method 5: Simplest options possible
            {'format': 'bestaudio', 'quiet': True, 'no_warnings': True, 'geo_bypass': True}
        ]
        
        # Try each method until one works
        last_error = None
        for i, method_opts in enumerate(extraction_methods):
            try:
                logger.info(f"Trying extraction method {i+1}/{len(extraction_methods)}")
                with yt_dlp.YoutubeDL(method_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Check if we got proper info
                    if not info or 'url' not in info:
                        raise Exception("Missing URL in extracted info")
                    
                    logger.info(f"Successfully extracted audio URL using method {i+1}")
                    return {
                        'url': info['url'],
                        'title': info.get('title', 'Unknown Title'),
                        'author': info.get('uploader', 'Unknown Author'),
                        'thumbnail': info.get('thumbnail', ''),
                        'auth_method': f"{auth_method_used}_method{i+1}"
                    }
            except Exception as e:
                logger.warning(f"Method {i+1} failed: {str(e)}")
                last_error = e
                continue
        
        # If we get here, all methods failed
        raise Exception(f"All extraction methods failed. Last error: {str(last_error)}")
                
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
