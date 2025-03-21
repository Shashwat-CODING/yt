import logging
import os
import json
import yt_dlp
import requests
import subprocess
import shlex
import concurrent.futures
import time
import signal
from socket import timeout as SocketTimeout
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    """Context manager to limit execution time of a block"""
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def test_proxy(proxy_url, timeout=2):
    """Test if a proxy is working by making a simple request with a short timeout"""
    try:
        test_url = "https://www.google.com"
        start_time = time.time()
        requests.get(test_url, proxies={"http": proxy_url, "https": proxy_url}, timeout=timeout)
        response_time = time.time() - start_time
        logger.info(f"Proxy {proxy_url} is working (response time: {response_time:.2f}s)")
        return True, response_time
    except Exception as e:
        logger.warning(f"Proxy {proxy_url} failed test: {str(e)}")
        return False, 999  # Large number to indicate failure

def extract_audio_url(url, max_timeout=30, proxy_timeout=4):
    """Extract audio stream URL from YouTube video using yt-dlp with proxy if available, otherwise direct"""
    try:
        # Define the path to the client secrets file relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        client_secrets_file = os.path.join(current_dir, 'client_secrets.json')
        
        # Create client_secrets.json if it doesn't exist
        if not os.path.exists(client_secrets_file):
            oauth_info = {
                "web": {
                    "client_id": "1023316916513-0ceeamcb82h4c5j27p7pnrbq0fl9udhd.apps.googleusercontent.com",
                    "project_id": "yt-metadata-442112",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": "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"
                }
            }
            with open(client_secrets_file, 'w') as f:
                json.dump(oauth_info, f)
            logger.info(f"Created client_secrets.json at {client_secrets_file}")
        
        # Check if cookies file exists
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        cookies_arg = f"--cookies {shlex.quote(cookies_path)}" if os.path.exists(cookies_path) else ""
        logger.info(f"Cookies path: {cookies_path}, exists: {os.path.exists(cookies_path)}")
        
        # First prepare direct connection options that we can use if proxy fails
        direct_ydl_opts = {
            'format': 'bestaudio',
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': max_timeout,
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        }
        
        if os.path.exists(cookies_path):
            direct_ydl_opts['cookiefile'] = cookies_path
        
        # Try to get proxies with a very short timeout to not delay direct connection
        working_proxies = []
        try:
            with time_limit(6):  # Hard limit on proxy discovery
                # Get proxies from the dynamic JSON with a short timeout
                response = requests.get(
                    "https://backendmix.vercel.app/ips", 
                    timeout=3
                )
                if response.status_code == 200:
                    proxy_data = response.json()
                    proxies = proxy_data.get('proxies', [])
                    logger.info(f"Fetched {len(proxies)} proxies")
                    
                    # Only test proxies if we actually got some, but don't spend too much time
                    if proxies:
                        # Quick test proxies concurrently with very tight timeout
                        working_proxies_with_times = []
                        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(proxies))) as executor:
                            future_to_proxy = {executor.submit(test_proxy, f"http://{proxy}", 2): proxy for proxy in proxies}
                            for future in concurrent.futures.as_completed(future_to_proxy, timeout=5):
                                proxy = future_to_proxy[future]
                                try:
                                    success, response_time = future.result()
                                    if success:
                                        working_proxies_with_times.append((proxy, response_time))
                                except Exception:
                                    pass
                        
                        # Sort proxies by response time (fastest first)
                        working_proxies_with_times.sort(key=lambda x: x[1])
                        working_proxies = [p[0] for p in working_proxies_with_times]
                        
                        if working_proxies:
                            logger.info(f"Found {len(working_proxies)} working proxies out of {len(proxies)}")
                        else:
                            logger.warning("No working proxies found, will use direct connection")
                else:
                    logger.warning("Failed to fetch proxies, will use direct connection")
        except (Exception, TimeoutException) as e:
            logger.warning(f"Error or timeout fetching/testing proxies: {str(e)}, will use direct connection")
            working_proxies = []  # Reset to empty in case of timeout
        
        # Try proxy if available, but with a strict timeout
        if working_proxies:
            # Only try the first (fastest) working proxy with a strict timeout
            try:
                proxy = working_proxies[0]  # Use only the fastest proxy
                proxy_url = f"http://{proxy}"
                logger.info(f"Trying with proxy: {proxy_url}")
                
                # Use a strict timeout for the proxy attempt
                with time_limit(proxy_timeout + 1):  # +1 second for overhead
                    ydl_opts = {
                        'format': 'bestaudio',
                        'quiet': True,
                        'no_warnings': True,
                        'socket_timeout': proxy_timeout,
                        'proxy': proxy_url,
                        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                    }
                    
                    if os.path.exists(cookies_path):
                        ydl_opts['cookiefile'] = cookies_path
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        logger.info(f"Successfully extracted with proxy: {proxy_url}")
                        return {
                            'url': info['url'],
                            'title': info['title'],
                            'author': info['uploader'],
                            'thumbnail': info['thumbnail']
                        }
            except (Exception, TimeoutException) as e:
                logger.warning(f"Proxy attempt failed or timed out: {str(e)}, switching to direct connection")
        else:
            logger.info("No working proxies, using direct connection")
        
        # If we reach here, proxy attempt either wasn't tried or failed
        # Use direct connection
        logger.info("Using direct connection")
        
        try:
            with yt_dlp.YoutubeDL(direct_ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logger.info("Successfully extracted with direct connection")
                return {
                    'url': info['url'],
                    'title': info['title'],
                    'author': info['uploader'],
                    'thumbnail': info['thumbnail']
                }
        except Exception as e:
            logger.warning(f"Direct connection failed: {str(e)}")
            
            # Final attempt: Try subprocess without proxy
            try:
                cmd = f"yt-dlp --socket-timeout {max_timeout} {cookies_arg} -f bestaudio --dump-json {shlex.quote(url)}"
                logger.info(f"Running subprocess without proxy: {cmd}")
                
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=max_timeout+2)
                if result.stdout:
                    info = json.loads(result.stdout)
                    logger.info("Successfully extracted with subprocess without proxy")
                    return {
                        'url': info.get('url', ''),
                        'title': info.get('title', ''),
                        'author': info.get('uploader', ''),
                        'thumbnail': info.get('thumbnail', '')
                    }
            except Exception as sub_e:
                logger.error(f"Final subprocess attempt failed: {str(sub_e)}")
                raise Exception(f"All extraction methods failed. Last error: {str(sub_e)}")
            
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
