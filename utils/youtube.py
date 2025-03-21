import os
import logging
import yt_dlp

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video using yt-dlp with cookies authentication"""
    try:
        # Define the path to the cookies file relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        
        # Check if cookies file exists
        if not os.path.exists(cookies_path):
            logger.warning(f"Cookies file not found at {cookies_path}. Authentication may fail.")
        
        # Configure yt-dlp options with cookies only
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'cookiefile': cookies_path,
            'socket_timeout': 15,
            'retries': 5
        }
        
        # Extract info
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Attempting to extract info using cookies")
                info = ydl.extract_info(url, download=False)
                logger.info(f"Successfully extracted info for {url}")
                return {
                    'url': info['url'],
                    'title': info['title'],
                    'author': info['uploader'],
                    'thumbnail': info['thumbnail']
                }
        except Exception as e:
            logger.error(f"Extraction attempt failed: {str(e)}")
            raise Exception(f"Failed to extract audio: {str(e)}")
    
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
