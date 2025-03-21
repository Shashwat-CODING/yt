import os
import logging
import yt_dlp

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video using yt-dlp with cookies authentication and proxy"""
    try:
        # Define the path to the cookies file relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        
        # Check if cookies file exists
        if not os.path.exists(cookies_path):
            logger.warning(f"Cookies file not found at {cookies_path}. Authentication may fail.")
        
        # Configure proxy settings
        proxy_url = "http://oc-09e255d5870d02aede572922193181eede3c75df75e8c0936f034667b9856636-country-IN-session-5457c:9x4d4i2fnq7g@proxy.oculus-proxy.com:31111"
        
        # Configure yt-dlp options with cookies and proxy
        ydl_opts = {
            'format': 'bestaudio/best',  # Try to get best audio, fallback to best available format
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'cookiefile': cookies_path,
            'socket_timeout': 30,
            'retries': 10,
            'proxy': proxy_url,
            'prefer_insecure': True,  # Sometimes needed for certain proxies
            'nocheckcertificate': True,  # Skip HTTPS certificate validation
            'ignoreerrors': True,  # Continue with partial information if possible
        }
        
        # First, list available formats to help with debugging
        logger.info(f"Listing available formats for {url}")
        list_formats_opts = ydl_opts.copy()
        list_formats_opts['listformats'] = True
        list_formats_opts['quiet'] = False
        try:
            with yt_dlp.YoutubeDL(list_formats_opts) as ydl:
                ydl.extract_info(url, download=False)
        except Exception as e:
            logger.warning(f"Format listing failed: {str(e)}")
        
        # Try extraction with multiple format attempts
        format_options = [
            'bestaudio/best',
            'bestaudio',
            'best',
            'worstaudio/worst'  # If nothing else works, try getting any format
        ]
        
        last_error = None
        for format_option in format_options:
            try:
                logger.info(f"Attempting extraction with format: {format_option}")
                current_opts = ydl_opts.copy()
                current_opts['format'] = format_option
                
                with yt_dlp.YoutubeDL(current_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Check if we successfully got a URL
                    if info and ('url' in info or 'requested_formats' in info):
                        logger.info(f"Successfully extracted info with format: {format_option}")
                        
                        # Handle different response structures
                        audio_url = None
                        if 'url' in info:
                            audio_url = info['url']
                        elif 'requested_formats' in info:
                            # Find audio format in the requested formats
                            for fmt in info['requested_formats']:
                                if fmt.get('acodec') != 'none':
                                    audio_url = fmt.get('url')
                                    break
                            # If no specific audio format, use the first available
                            if not audio_url and info['requested_formats']:
                                audio_url = info['requested_formats'][0].get('url')
                        
                        if audio_url:
                            return {
                                'url': audio_url,
                                'title': info.get('title', 'Unknown Title'),
                                'author': info.get('uploader', 'Unknown Uploader'),
                                'thumbnail': info.get('thumbnail', '')
                            }
                        else:
                            logger.warning("No URL found in extracted info")
                    else:
                        logger.warning("Extraction returned no usable info")
            
            except Exception as e:
                last_error = e
                logger.warning(f"Extraction attempt with format {format_option} failed: {str(e)}")
                continue
        
        # If we reach here, all attempts failed
        if last_error:
            raise Exception(f"All format extraction attempts failed: {str(last_error)}")
        else:
            raise Exception("Failed to extract any audio URL")
    
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
