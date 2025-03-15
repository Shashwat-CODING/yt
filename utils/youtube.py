import logging
import os
import yt_dlp
import random

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video using yt-dlp with enhanced 403 error prevention"""
    try:
        # Define the path to the cookies file relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        
        # List of common user agents to rotate
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
        ]
        
        # Configure yt-dlp options with cookies and improved settings
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': random.choice(user_agents),
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'geo_bypass': True,  # Add geo bypass option
            'geo_bypass_country': 'US',  # Specify country for geo bypass
            'extractor_retries': 3,  # Retry extraction multiple times
            'source_address': '0.0.0.0',  # Use any available network interface
        }
        
        # Log if cookies file is found or not
        if os.path.exists(cookies_path):
            logger.info(f"Using cookies file: {cookies_path}")
        else:
            logger.warning(f"Cookies file not found at {cookies_path}")
        
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
