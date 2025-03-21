import os
import logging
import yt_dlp
import re

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
        
        # Try to detect if it's a normal video or shorts/embed
        video_id = None
        if 'youtube.com/watch?v=' in url:
            match = re.search(r'watch\?v=([a-zA-Z0-9_-]+)', url)
            if match:
                video_id = match.group(1)
        elif 'youtu.be/' in url:
            match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
            if match:
                video_id = match.group(1)
        
        # If we found a video ID, try alternative URLs
        if video_id:
            original_url = url
            alternative_urls = [
                original_url,
                f"https://www.youtube.com/embed/{video_id}",  # Try embed URL
                f"https://www.youtube.com/shorts/{video_id}",  # Try shorts URL
                f"https://m.youtube.com/watch?v={video_id}",  # Try mobile URL
                f"https://www.youtube-nocookie.com/watch?v={video_id}"  # Try privacy-enhanced URL
            ]
        else:
            alternative_urls = [url]  # Just use the original URL
            
        # Configure yt-dlp options with cookies and proxy
        base_ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'cookiefile': cookies_path,
            'socket_timeout': 30,
            'retries': 10,
            'proxy': proxy_url,
            'prefer_insecure': True,  # Sometimes needed for certain proxies
            'nocheckcertificate': True,  # Skip HTTPS certificate validation
            'ignoreerrors': True,  # Continue with partial information if possible
            'allow_unplayable_formats': True,  # Try to extract even unplayable formats
            'youtube_include_dash_manifest': True,  # Include DASH manifests
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],  # Try using web client
                    'player_skip': ['js', 'configs'],  # Skip some extraction steps for speed
                }
            }
        }
        
        # Format options to try
        format_options = [
            'bestaudio/best',
            'bestaudio',
            'best',
            'worstaudio/worst',
            '140/160/18/22'  # Specific format IDs that often work
        ]
        
        # Try each alternative URL with each format option
        for alt_url in alternative_urls:
            logger.info(f"Trying alternative URL: {alt_url}")
            
            # First, list available formats for debugging
            try:
                list_formats_opts = base_ydl_opts.copy()
                list_formats_opts['listformats'] = True
                list_formats_opts['quiet'] = False
                
                with yt_dlp.YoutubeDL(list_formats_opts) as ydl:
                    logger.info(f"Listing available formats for {alt_url}")
                    ydl.extract_info(alt_url, download=False)
            except Exception as e:
                logger.warning(f"Format listing failed for {alt_url}: {str(e)}")
            
            # Try each format option
            for format_option in format_options:
                try:
                    logger.info(f"Attempting extraction with URL {alt_url} and format: {format_option}")
                    current_opts = base_ydl_opts.copy()
                    current_opts['format'] = format_option
                    
                    with yt_dlp.YoutubeDL(current_opts) as ydl:
                        info = ydl.extract_info(alt_url, download=False)
                        
                        # Check if we successfully got a URL
                        if info:
                            # Direct URL in info
                            if 'url' in info and info['url']:
                                logger.info(f"Successfully extracted direct URL")
                                return {
                                    'url': info['url'],
                                    'title': info.get('title', 'Unknown Title'),
                                    'author': info.get('uploader', 'Unknown Uploader'),
                                    'thumbnail': info.get('thumbnail', '')
                                }
                            
                            # Check for requested formats
                            if 'requested_formats' in info and info['requested_formats']:
                                # Find audio format in the requested formats
                                for fmt in info['requested_formats']:
                                    if fmt.get('acodec') != 'none' and 'url' in fmt:
                                        logger.info(f"Found audio format in requested_formats")
                                        return {
                                            'url': fmt['url'],
                                            'title': info.get('title', 'Unknown Title'),
                                            'author': info.get('uploader', 'Unknown Uploader'),
                                            'thumbnail': info.get('thumbnail', '')
                                        }
                                
                                # If no specific audio format, use the first available
                                if info['requested_formats'][0].get('url'):
                                    logger.info(f"Using first available format")
                                    return {
                                        'url': info['requested_formats'][0]['url'],
                                        'title': info.get('title', 'Unknown Title'),
                                        'author': info.get('uploader', 'Unknown Uploader'),
                                        'thumbnail': info.get('thumbnail', '')
                                    }
                            
                            # Check for formats list
                            if 'formats' in info and info['formats']:
                                # Try to find an audio format first
                                for fmt in info['formats']:
                                    if fmt.get('acodec') != 'none' and 'url' in fmt:
                                        logger.info(f"Found audio format in formats list")
                                        return {
                                            'url': fmt['url'],
                                            'title': info.get('title', 'Unknown Title'),
                                            'author': info.get('uploader', 'Unknown Uploader'),
                                            'thumbnail': info.get('thumbnail', '')
                                        }
                                
                                # If no audio format, use any format with a URL
                                for fmt in info['formats']:
                                    if 'url' in fmt:
                                        logger.info(f"Using any available format with URL")
                                        return {
                                            'url': fmt['url'],
                                            'title': info.get('title', 'Unknown Title'),
                                            'author': info.get('uploader', 'Unknown Uploader'),
                                            'thumbnail': info.get('thumbnail', '')
                                        }
                            
                            logger.warning("No URL found in extracted info")
                        else:
                            logger.warning("Extraction returned no usable info")
                
                except Exception as e:
                    logger.warning(f"Extraction attempt with URL {alt_url} and format {format_option} failed: {str(e)}")
                    continue
        
        # If all attempts failed, try a direct download approach
        try:
            logger.info("Attempting direct download approach as last resort")
            direct_opts = base_ydl_opts.copy()
            direct_opts['format'] = 'best'
            direct_opts['simulate'] = True
            direct_opts['quiet'] = False
            direct_opts['skip_download'] = True
            direct_opts['youtube_include_dash_manifest'] = True
            
            with yt_dlp.YoutubeDL(direct_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                if info_dict and ('url' in info_dict or 'formats' in info_dict):
                    if 'url' in info_dict:
                        return {
                            'url': info_dict['url'],
                            'title': info_dict.get('title', 'Unknown Title'),
                            'author': info_dict.get('uploader', 'Unknown Uploader'),
                            'thumbnail': info_dict.get('thumbnail', '')
                        }
                    elif 'formats' in info_dict and info_dict['formats']:
                        # Get the best format with a URL
                        for fmt in info_dict['formats']:
                            if 'url' in fmt:
                                return {
                                    'url': fmt['url'],
                                    'title': info_dict.get('title', 'Unknown Title'),
                                    'author': info_dict.get('uploader', 'Unknown Uploader'),
                                    'thumbnail': info_dict.get('thumbnail', '')
                                }
        except Exception as e:
            logger.error(f"Direct download approach failed: {str(e)}")
        
        # If we reach here, all attempts failed
        raise Exception("All extraction methods failed to get an audio URL")
    
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
