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
        # Using a more flexible format selection to prevent format errors
        ydl_opts = {
            'format': 'bestaudio',  # More forgiving format selection
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
                    'url': info.get('url', ''),
                    'title': info.get('title', 'Unknown Title'),
                    'author': info.get('uploader', 'Unknown Uploader'),
                    'thumbnail': info.get('thumbnail', '')
                }
        except yt_dlp.utils.DownloadError as format_error:
            logger.warning(f"Format error: {str(format_error)}")
            
            # Try again with a different format specification
            logger.info("Trying with a more generic format selector")
            ydl_opts['format'] = 'best'  # Try with any available format
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"Successfully extracted info with fallback format")
                    return {
                        'url': info.get('url', ''),
                        'title': info.get('title', 'Unknown Title'),
                        'author': info.get('uploader', 'Unknown Uploader'),
                        'thumbnail': info.get('thumbnail', '')
                    }
            except Exception as fallback_error:
                logger.error(f"Fallback extraction failed: {str(fallback_error)}")
                raise Exception(f"Failed to extract with fallback format: {str(fallback_error)}")
                
        except Exception as e:
            logger.error(f"Extraction attempt failed: {str(e)}")
            raise Exception(f"Failed to extract audio: {str(e)}")
    
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
