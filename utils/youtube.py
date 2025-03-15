import logging
import os
import yt_dlp
import random
import requests
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
import threading

logger = logging.getLogger(__name__)

# Keep-alive functionality for Render
def keep_render_awake(url, interval=14*60):
    """
    Pings a URL at regular intervals to keep a Render instance awake
    
    Args:
        url (str): The URL to ping (your Render app URL)
        interval (int): Time between pings in seconds (default: 14 minutes)
    """
    def ping_periodically():
        while True:
            try:
                logger.info(f"Sending keep-alive ping to {url}")
                requests.get(url, timeout=10)
                logger.info("Keep-alive ping successful")
            except Exception as e:
                logger.error(f"Keep-alive ping failed: {str(e)}")
            
            # Sleep until next ping
            time.sleep(interval)
    
    # Start the ping in a daemon thread so it doesn't block program exit
    ping_thread = threading.Thread(target=ping_periodically, daemon=True)
    ping_thread.start()
    logger.info(f"Started keep-alive service, pinging {url} every {interval} seconds")
    return ping_thread

def fetch_proxy_instances():
    """Fetch available proxy instances"""
    try:
        response = requests.get("https://raw.githubusercontent.com/n-ce/Uma/main/dynamic_instances.json", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to fetch proxy instances, status code: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error fetching proxy instances: {str(e)}")
    
    # Default fallback instances if fetch fails
    return {
        "piped": [
            "https://pipedapi.drgns.space",
            "https://pipedapi.adminforge.de",
            "https://nyc1.piapi.ggtyler.dev",
            "https://pipedapi.leptons.xyz"
        ],
        "invidious": [
            "https://invidious.nikkosphere.com",
            "https://invidious.f5.si"
        ]
    }

def is_url_accessible(url, timeout=5):
    """Check if URL is accessible with HEAD and GET requests"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        # Try HEAD request first (faster)
        try:
            response = requests.head(url, timeout=timeout/2, headers=headers, allow_redirects=True)
            # Status 403 might allow GET still, so only return True for success codes
            if 200 <= response.status_code < 300:
                return True
        except:
            pass
            
        # If HEAD fails or returns 403, try GET for a few bytes
        try:
            response = requests.get(url, timeout=timeout, headers=headers, stream=True)
            # Read just a small part to confirm it works
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    return True
                break
            return 200 <= response.status_code < 400
        except:
            return False
    except Exception as e:
        logger.debug(f"URL accessibility check failed: {str(e)}")
        return False

def extract_video_id(url):
    """Extract video ID from YouTube or YouTube Music URL"""
    if 'v=' in url:
        return url.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0]
    return None

def proxy_url_through_piped(audio_url, video_id, proxy_instances):
    """Convert direct googlevideo URL to a proxied version via Piped or Invidious"""
    # Parse original URL components
    parsed = urllib.parse.urlparse(audio_url)
    query_params = urllib.parse.parse_qs(parsed.query)
    
    # Add original host to query parameters
    query_params['host'] = [parsed.netloc]
    
    # Build new query string
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    
    # Function to test a proxy instance
    def test_proxy(instance):
        if "piped" in instance:
            # Piped audio proxy format
            proxied_url = f"{instance}/streams/{video_id}"
            try:
                response = requests.get(proxied_url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    # Prioritize opus format
                    audio_streams = [s for s in data.get("audioStreams", []) 
                                     if "opus" in s.get("mimeType", "").lower() or 
                                     "webm" in s.get("mimeType", "").lower()]
                    
                    # Fall back to any audio if no opus
                    if not audio_streams:
                        audio_streams = data.get("audioStreams", [])
                        
                    if audio_streams:
                        # Sort to prefer opus format and higher quality
                        audio_streams.sort(key=lambda s: (
                            "opus" in s.get("mimeType", "").lower(),
                            int(s.get("bitrate", 0))
                        ), reverse=True)
                        
                        url = audio_streams[0].get("url")
                        if url and is_url_accessible(url):
                            return url
                return None
            except:
                return None
        elif "invidious" in instance:
            # Invidious format directly replaces the host
            proxied_path = f"/videoplayback?{new_query}"
            proxied_url = f"{instance}{proxied_path}"
            if is_url_accessible(proxied_url):
                return proxied_url
            return None
    
    # Test all instances in parallel
    valid_proxies = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        piped_futures = {executor.submit(test_proxy, instance): instance for instance in proxy_instances.get("piped", [])}
        invidious_futures = {executor.submit(test_proxy, instance): instance for instance in proxy_instances.get("invidious", [])}
        
        # Check results as they complete
        for future in as_completed(list(piped_futures.keys()) + list(invidious_futures.keys())):
            result = future.result()
            if result:
                valid_proxies.append(result)
                # Break early if we have a valid proxy
                if len(valid_proxies) >= 1:
                    executor._threads.clear()
                    break
    
    return valid_proxies[0] if valid_proxies else None

def extract_audio_url(url, keep_alive_url=None):
    """Extract audio stream URL from YouTube Music with failover to proxy methods"""
    # Setup keep-alive ping if URL provided
    if keep_alive_url:
        keep_render_awake(keep_alive_url)
    
    # Start timing
    start_time = time.time()
    
    # Extract video ID for potential proxy fallback
    video_id = extract_video_id(url)
    if not video_id:
        logger.error("Could not extract video ID from URL")
        return None
    
    # Fetch proxy instances in the background while trying direct extraction
    proxy_instances = {}
    
    def fetch_proxies():
        nonlocal proxy_instances
        proxy_instances = fetch_proxy_instances()
    
    # Start proxy fetching in background
    with ThreadPoolExecutor(max_workers=1) as executor:
        proxy_future = executor.submit(fetch_proxies)
    
    try:
        # Define the path to the cookies file relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        
        # Use a single optimal user agent
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Optimize yt-dlp options for speed, prioritizing opus format
        ydl_opts = {
            'format': 'bestaudio[acodec=opus]/bestaudio[acodec=vorbis]/bestaudio',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': user_agent,
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
            'nocheckcertificate': True,
            'socket_timeout': 8,
            'geo_bypass': True,
            'extractor_retries': 1,
            'retries': 1,
            'skip_download': True,
            'http_headers': {
                'Accept-Language': 'en-IN,hi-IN;q=0.9,hi;q=0.8,en-US;q=0.7,en;q=0.6',
                'Referer': 'https://music.youtube.com/',
            },
        }
        
        # Convert to music.youtube.com URL if needed
        if 'music.youtube.com' not in url and video_id:
            url = f"https://music.youtube.com/watch?v={video_id}"
        
        # Direct extraction attempt
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            audio_url = None
            if 'formats' in info and len(info['formats']) > 0:
                # Filter for opus audio formats first
                opus_formats = [f for f in info['formats'] 
                              if f.get('acodec', '').startswith('opus') and 
                              not f.get('resolution')]
                
                # If no opus, try any audio
                if opus_formats:
                    # Sort by quality (highest first)
                    opus_formats.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
                    audio_url = opus_formats[0]['url']
                    audio_format = 'opus'
                else:
                    # Try other audio formats
                    audio_formats = [f for f in info['formats'] 
                                  if 'audio' in f.get('format', '').lower() and 
                                  not f.get('resolution')]
                    
                    if audio_formats:
                        audio_formats.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
                        audio_url = audio_formats[0]['url']
                        audio_format = audio_formats[0].get('acodec', 'unknown')
                    else:
                        audio_url = info.get('url', '')
                        audio_format = 'unknown'
            else:
                audio_url = info.get('url', '')
                audio_format = 'unknown'
                
            # Check if URL is valid
            if audio_url and is_url_accessible(audio_url):
                result = {
                    'url': audio_url,
                    'title': info.get('title', 'Unknown Title'),
                    'author': info.get('uploader', 'Unknown Uploader'),
                    'thumbnail': info.get('thumbnail', None),
                    'format': audio_format,
                    'duration': time.time() - start_time
                }
                logger.info(f"Direct extraction successful in {result['duration']:.2f} seconds")
                return result
            else:
                logger.warning("Direct audio URL extraction failed or URL not accessible")
                
    except Exception as e:
        logger.error(f"Direct extraction failed: {str(e)}")
    
    # Wait for proxy instances to be fetched if needed
    if not proxy_future.done():
        try:
            # Wait with timeout
            proxy_instances = proxy_future.result(timeout=3)
        except Exception as e:
            logger.warning(f"Error waiting for proxy instances: {str(e)}")
    
    # Try proxy fallback
    try:
        logger.info("Attempting to extract via proxy method")
        
        # Try to get minimal info via ytdlp
        ydl_opts = {
            'format': 'bestaudio[acodec=opus]/bestaudio',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'force_generic_extractor': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown Title')
            author = info.get('uploader', 'Unknown Uploader')
            thumbnail = info.get('thumbnail', None)
            
            # Try to get an audio URL
            formats = info.get('formats', [])
            audio_url = None
            
            # Look for opus format specifically first
            opus_formats = [f for f in formats if f.get('acodec', '').startswith('opus')]
            
            if opus_formats:
                audio_url = opus_formats[0]['url']
                audio_format = 'opus'
            elif formats:
                audio_formats = [f for f in formats if 'audio' in f.get('format', '').lower()]
                if audio_formats:
                    audio_url = audio_formats[0]['url']
                    audio_format = audio_formats[0].get('acodec', 'unknown')
            
            if not audio_url and info.get('url'):
                audio_url = info.get('url')
                audio_format = 'unknown'
            
            # If we have an audio URL but it's not accessible (e.g., 403), try proxying
            if audio_url and not is_url_accessible(audio_url):
                proxied_url = proxy_url_through_piped(audio_url, video_id, proxy_instances)
                
                if proxied_url and is_url_accessible(proxied_url):
                    result = {
                        'url': proxied_url, 
                        'proxied': True,
                        'original_url': audio_url,
                        'title': title,
                        'author': author,
                        'thumbnail': thumbnail,
                        'format': audio_format,
                        'duration': time.time() - start_time
                    }
                    logger.info(f"Proxy extraction successful in {result['duration']:.2f} seconds")
                    return result
    
    except Exception as e:
        logger.error(f"Proxy extraction failed: {str(e)}")
    
    # If we reached here, all methods failed
    logger.error("All extraction methods failed")
    return {
        'error': "All extraction methods failed. This track may be heavily restricted.",
        'duration': time.time() - start_time
    }

# Example usage of the keep-alive functionality
# To use this, call your extract_audio_url with a keep_alive_url parameter
# e.g., extract_audio_url("https://music.youtube.com/watch?v=...", keep_alive_url="https://your-app-name
