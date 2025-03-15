import logging
import os
import yt_dlp
import random
import time

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video for India without using proxies"""
    try:
        # Define the path to the cookies file relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        
        # List of diverse user agents to avoid fingerprinting
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        ]
        
        # Configure yt-dlp options with all possible non-proxy bypasses
        ydl_opts = {
            'format': 'bestaudio/best[acodec^=opus]/best[acodec^=vorbis]/best[acodec^=aac]/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': random.choice(user_agents),
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
            'nocheckcertificate': True,
            'socket_timeout': 60,  # Increased timeout
            'geo_bypass': True,
            'geo_bypass_country': 'IN',
            'extractor_retries': 10,
            'retries': 15,
            'fragment_retries': 15,
            'skip_download': True,
            'source_address': '0.0.0.0',
            'http_headers': {
                'Accept-Language': 'en-IN,hi-IN;q=0.9,hi;q=0.8,en-US;q=0.7,en;q=0.6',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Referer': 'https://www.youtube.com/',
                'Origin': 'https://www.youtube.com',
                'Sec-Fetch-Dest': 'audio',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'DNT': '1',
            },
            'prefer_insecure': True,  # Try non-HTTPS if HTTPS fails
            'sleep_interval': 2,  # Add sleep between requests
        }
        
        if os.path.exists(cookies_path):
            logger.info(f"Using cookies file: {cookies_path}")
        else:
            logger.warning(f"Cookies file not found at {cookies_path}")
            logger.info("Trying to extract without cookies - this may limit success rate")
        
        # Add random delay before starting
        time.sleep(random.uniform(1, 3))
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First try with normal extraction
            info = ydl.extract_info(url, download=False)
            
            # Check if we have formats and try to find one that doesn't use the problematic server
            if 'formats' in info and len(info['formats']) > 0:
                formats = info['formats']
                
                # First look for formats without the problematic domain
                for fmt in formats:
                    format_url = fmt.get('url', '')
                    if 'nx5s7nel.googlevideo.com' not in format_url and 'audio' in fmt.get('format', '').lower():
                        logger.info(f"Found alternate audio server URL")
                        selected_url = format_url
                        break
                else:
                    # If all problematic, try lowest bitrate which may have fewer restrictions
                    audio_formats = [f for f in formats if 'audio' in f.get('format', '').lower()]
                    if audio_formats:
                        # Sort by bitrate, lowest first
                        audio_formats.sort(key=lambda x: x.get('abr', 0) or 0)
                        selected_url = audio_formats[0]['url']
                        logger.info(f"Using lowest bitrate audio to avoid restrictions")
                    else:
                        selected_url = info['url']
            else:
                selected_url = info['url']
            
            return {
                'url': selected_url,
                'title': info.get('title', 'Unknown Title'),
                'author': info.get('uploader', 'Unknown Uploader'),
                'thumbnail': info.get('thumbnail', None)
            }
                
    except Exception as e:
        logger.error(f"Standard extraction failed: {str(e)}")
        
        # If standard extraction fails, try alternative formats and methods
        try:
            logger.info("Attempting extraction with alternative format selectors...")
            
            # Try with m4a format specifically, which often has fewer restrictions
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio/best'
            
            # More aggressive settings
            ydl_opts['force_generic_extractor'] = True
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'url': info.get('url', ''),
                    'title': info.get('title', 'Unknown Title'),
                    'author': info.get('uploader', 'Unknown Uploader'),
                    'thumbnail': info.get('thumbnail', None)
                }
        except Exception as second_error:
            logger.error(f"Alternative extraction also failed: {str(second_error)}")
            
            # Last resort - use embed page extraction which sometimes bypasses restrictions
            try:
                logger.info("Attempting final extraction method...")
                ydl_opts['force_generic_extractor'] = False
                ydl_opts['extract_flat'] = True
                ydl_opts['youtube_include_dash_manifest'] = False
                
                # Construct embed URL which may have different restrictions
                if 'youtube.com' in url or 'youtu.be' in url:
                    video_id = None
                    if 'v=' in url:
                        video_id = url.split('v=')[1].split('&')[0]
                    elif 'youtu.be/' in url:
                        video_id = url.split('youtu.be/')[1].split('?')[0]
                    
                    if video_id:
                        embed_url = f"https://www.youtube.com/embed/{video_id}"
                        logger.info(f"Trying embed URL: {embed_url}")
                        
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(embed_url, download=False)
                            return {
                                'url': info.get('url', ''),
                                'title': info.get('title', 'Unknown Title'),
                                'author': info.get('uploader', 'Unknown Uploader'),
                                'thumbnail': info.get('thumbnail', None)
                            }
                
                raise Exception("Failed to extract with embed method")
            except:
                raise Exception(f"All extraction methods failed. This video may be heavily restricted in your region.")
