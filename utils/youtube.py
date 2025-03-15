import logging
import os
import yt_dlp
import random
import time
import requests
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

logger = logging.getLogger(__name__)

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
    """Check if URL is accessible with HEAD request"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        # Use HEAD request which is much faster than GET
        response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        # Check if status code is in 2xx range or 3xx range
        return 200 <= response.status_code < 400
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
                    audio_streams = [s for s in data.get("audioStreams", []) if s.get("quality") == "medium" or "opus" in s.get("mimeType", "")]
                    if audio_streams:
                        return audio_streams[0].get("url")
                return None
            except:
                return None
        elif "invidious" in instance:
            # Invidious format directly replaces the host
            proxied_path = f"/videoplayback?{new_query}"
            proxied_url = f"{instance}{proxied_path}"
            if is_url_accessible(proxied_url, timeout=3):
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

def extract_audio_url(url):
    """Extract audio stream URL from YouTube Music with failover to proxy methods"""
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
        
        # Use a single optimal user agent instead of random selection
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Optimize yt-dlp options for speed
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': user_agent,
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
            'nocheckcertificate': True,
            'socket_timeout': 8,  # Reduced timeout for faster failure
            'geo_bypass': True,
            'extractor_retries': 1,  # Reduced retries for speed
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
                # Filter for audio-only formats
                audio_formats = [f for f in info['formats'] if 'audio' in f.get('format', '').lower() and not f.get('resolution')]
                if audio_formats:
                    # Sort by quality (highest first)
                    audio_formats.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
                    audio_url = audio_formats[0]['url']
                else:
                    audio_url = info.get('url', '')
            else:
                audio_url = info.get('url', '')
                
            # Check if URL is valid
            if audio_url and is_url_accessible(audio_url):
                result = {
                    'url': audio_url,
                    'title': info.get('title', 'Unknown Title'),
                    'author': info.get('uploader', 'Unknown Uploader'),
                    'thumbnail': info.get('thumbnail', None),
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
            'format': 'bestaudio',
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
            
            if formats:
                audio_formats = [f for f in formats if 'audio' in f.get('format', '').lower()]
                if audio_formats:
                    audio_url = audio_formats[0]['url']
            
            if not audio_url and info.get('url'):
                audio_url = info.get('url')
            
            # If we have an audio URL but it's not accessible, try proxying
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
