import logging
import os
import yt_dlp
import random
import time
import re

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube Music for India without using proxies"""
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
        
        # Extract video ID from various YouTube Music URL formats
        video_id = None
        
        # Direct YouTube Music watch URLs
        if 'music.youtube.com/watch' in url and 'v=' in url:
            video_id = re.search(r'v=([^&]+)', url).group(1)
        # YouTube Music shortened URLs
        elif 'music.youtube.com/playlist' in url and 'list=' in url:
            playlist_id = re.search(r'list=([^&]+)', url).group(1)
            logger.info(f"YouTube Music playlist detected: {playlist_id}")
            # For playlists, we'll need to extract the first video ID
            temp_opts = {
                'quiet': True,
                'extract_flat': True,
                'dump_single_json': True,
                'skip_download': True,
            }
            with yt_dlp.YoutubeDL(temp_opts) as ydl:
                playlist_info = ydl.extract_info(url, download=False)
                if 'entries' in playlist_info and len(playlist_info['entries']) > 0:
                    video_id = playlist_info['entries'][0]['id']
                    logger.info(f"Extracted first video ID from playlist: {video_id}")
        # Handle video ID directly for any YouTube URL
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
        elif 'youtube.com/watch' in url and 'v=' in url:
            video_id = re.search(r'v=([^&]+)', url).group(1)
        
        # If we couldn't extract a video ID, try to use the URL directly
        if not video_id:
            logger.warning("Could not extract video ID. Will try to use the URL directly.")
        else:
            logger.info(f"Extracted video ID: {video_id}")
            # For YouTube Music, we'll use the regular YouTube URL for extraction
            # but set the proper headers for YouTube Music
            url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Configure yt-dlp options with YouTube Music specific settings
        ydl_opts = {
            # Prefer audio formats with best quality
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'user_agent': random.choice(user_agents),
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
            'nocheckcertificate': True,
            'socket_timeout': 60,
            'geo_bypass': True,
            'geo_bypass_country': 'IN',
            'extractor_retries': 10,
            'retries': 15,
            'fragment_retries': 15,
            'skip_download': True,
            'noplaylist': True,  # Avoid playlist expansion
            'http_headers': {
                'Accept-Language': 'en-IN,hi-IN;q=0.9,hi;q=0.8,en-US;q=0.7,en;q=0.6',
                'Accept': '*/*',
                'Referer': 'https://music.youtube.com/',
                'Origin': 'https://music.youtube.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'X-YouTube-Client-Name': '67',  # YouTube Music client ID
                'X-YouTube-Client-Version': '1.20240301.00.00',
                'DNT': '1',
            },
            'youtube_include_dash_manifest': True,
            'youtube_include_hls_manifest': True,
        }
        
        if os.path.exists(cookies_path):
            logger.info(f"Using cookies file: {cookies_path}")
        else:
            logger.warning(f"Cookies file not found at {cookies_path}")
        
        # Add random delay before starting to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First try with standard YouTube extraction - this works better for YouTube Music
            info = ydl.extract_info(url, download=False)
            
            # Get available formats
            formats = info.get('formats', [])
            
            # First try to get a pure audio format
            audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            
            if audio_formats:
                # Sort by quality (audio bitrate)
                audio_formats.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
                selected_format = audio_formats[0]
                selected_url = selected_format.get('url', '')
                logger.info(f"Selected audio format: {selected_format.get('format_id')} - {selected_format.get('abr')}kbps")
            else:
                # If no pure audio, get format with audio
                formats_with_audio = [f for f in formats if f.get('acodec') != 'none']
                if formats_with_audio:
                    # Sort by audio quality
                    formats_with_audio.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
                    selected_format = formats_with_audio[0]
                    selected_url = selected_format.get('url', '')
                    logger.info(f"No pure audio format available. Selected mixed format: {selected_format.get('format_id')}")
                else:
                    # Fallback to default
                    selected_url = info.get('url', '')
                    logger.warning("No format with audio found. Using default URL.")
            
            # Check if URL is valid
            if not selected_url:
                raise Exception("Failed to extract a valid audio URL")
            
            return {
                'url': selected_url,
                'title': info.get('title', 'Unknown Title'),
                'author': info.get('uploader', 'Unknown Uploader'),
                'thumbnail': info.get('thumbnail', None),
                'duration': info.get('duration', 0)
            }
                
    except Exception as e:
        logger.error(f"Standard extraction failed: {str(e)}")
        
        # If standard extraction fails, try with YouTube Music specific format selectors
        try:
            logger.info("Attempting extraction with YouTube Music specific options...")
            
            # YouTube Music specific approach
            ydl_opts['format'] = 'bestaudio[acodec=opus]/bestaudio'
            ydl_opts['youtube_include_dash_manifest'] = True
            ydl_opts['extractor_args'] = {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage', 'configs'],
                    'compat_opt': ['no-youtube-unavailable-videos']
                }
            }
            
            # Sometimes using a different extractor helps
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Get the best audio URL
                formats = info.get('formats', [])
                audio_formats = [f for f in formats if f.get('acodec') != 'none']
                
                if audio_formats:
                    # Sort by audio quality
                    audio_formats.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
                    selected_url = audio_formats[0].get('url', '')
                else:
                    selected_url = info.get('url', '')
                
                return {
                    'url': selected_url,
                    'title': info.get('title', 'Unknown Title'),
                    'author': info.get('uploader', 'Unknown Uploader'),
                    'thumbnail': info.get('thumbnail', None),
                    'duration': info.get('duration', 0)
                }
        except Exception as second_error:
            logger.error(f"YouTube Music specific extraction failed: {str(second_error)}")
            
            # Last resort - use a completely different approach
            try:
                logger.info("Attempting final extraction method for YouTube Music...")
                
                # For the final attempt, we'll use YouTube's innertube API which YouTube Music also uses
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'bestaudio',
                    'user_agent': random.choice(user_agents),
                    'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
                    'skip_download': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android_music', 'web_music'],
                            'compat_opt': ['no-youtube-unavailable-videos']
                        }
                    },
                    'http_headers': {
                        'Accept-Language': 'en-IN,hi-IN;q=0.9,hi;q=0.8,en-US;q=0.7,en;q=0.6',
                        'X-YouTube-Client-Name': '67',  # YouTube Music web client
                        'X-YouTube-Client-Version': '1.20240301.00.00'
                    }
                }
                
                # Create a fresh URL that will definitely work with YouTube's backend
                if video_id:
                    url = f"https://www.youtube.com/watch?v={video_id}"
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Get the URL from the best audio format
                    formats = info.get('formats', [])
                    audio_formats = [f for f in formats if f.get('acodec') != 'none']
                    
                    if audio_formats:
                        # For YouTube Music, we want the highest audio quality
                        audio_formats.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
                        selected_url = audio_formats[0].get('url', '')
                    else:
                        selected_url = info.get('url', '')
                    
                    return {
                        'url': selected_url,
                        'title': info.get('title', 'Unknown Title'),
                        'author': info.get('uploader', 'Unknown Uploader'),
                        'thumbnail': info.get('thumbnail', None),
                        'duration': info.get('duration', 0)
                    }
            except Exception as third_error:
                logger.error(f"All extraction methods failed: {str(third_error)}")
                raise Exception(f"Could not extract audio from YouTube Music. This track may be region-restricted or require authentication.")
