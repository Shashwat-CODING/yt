import logging
import os
import json
import yt_dlp
import requests
import subprocess
import shlex
import concurrent.futures
import time
from socket import timeout as SocketTimeout

logger = logging.getLogger(__name__)

def test_proxy(proxy_url, timeout=3):
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

def extract_audio_url(url, max_timeout=30, proxy_timeout=5):
    """Extract audio stream URL from YouTube video using yt-dlp with quick proxy switching and direct fallback"""
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
        
        # Get proxies from the dynamic JSON with a short timeout
        try:
            response = requests.get(
                "https://github.com/Shashwat-CODING/story/raw/refs/heads/main/wpr.json", 
                timeout=5
            )
            if response.status_code == 200:
                proxy_data = response.json()
                proxies = proxy_data.get('proxies', [])
                logger.info(f"Fetched {len(proxies)} proxies")
            else:
                proxies = []
                logger.warning("Failed to fetch proxies, proceeding without proxies")
        except Exception as e:
            proxies = []
            logger.warning(f"Error fetching proxies: {str(e)}")
        
        # Quick initial attempt without proxy (with short timeout)
        direct_connection_attempted = False
        try:
            logger.info("Initial attempt: Trying direct connection without proxy")
            ydl_opts = {
                'format': 'bestaudio',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 8,  # Short timeout for initial attempt
                'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            }
            
            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logger.info("Successfully extracted without proxy")
                return {
                    'url': info['url'],
                    'title': info['title'],
                    'author': info['uploader'],
                    'thumbnail': info['thumbnail']
                }
        except Exception as e:
            direct_connection_attempted = True
            logger.warning(f"Initial direct connection failed: {str(e)}")
            
        # Quick test all proxies concurrently
        working_proxies_with_times = []
        if proxies:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(proxies))) as executor:
                future_to_proxy = {executor.submit(test_proxy, f"http://{proxy}", 3): proxy for proxy in proxies}
                for future in concurrent.futures.as_completed(future_to_proxy, timeout=8):
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
                logger.warning("No working proxies found")
        else:
            working_proxies = []
            
        # Try proxies if available
        if working_proxies:
            for proxy in working_proxies:
                try:
                    proxy_url = f"http://{proxy}"
                    logger.info(f"Trying with proxy: {proxy_url}")
                    
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
                except Exception as e:
                    logger.warning(f"Failed with proxy {proxy}: {str(e)}")
                    
                    # Try subprocess approach with the same proxy
                    try:
                        cmd = f"yt-dlp --socket-timeout {proxy_timeout} --proxy {shlex.quote(proxy_url)} {cookies_arg} -f bestaudio --dump-json {shlex.quote(url)}"
                        logger.info(f"Running subprocess with proxy: {cmd}")
                        
                        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=proxy_timeout+2)
                        if result.stdout:
                            info = json.loads(result.stdout)
                            logger.info(f"Successfully extracted with subprocess and proxy: {proxy_url}")
                            return {
                                'url': info.get('url', ''),
                                'title': info.get('title', ''),
                                'author': info.get('uploader', ''),
                                'thumbnail': info.get('thumbnail', '')
                            }
                    except Exception as sub_e:
                        logger.warning(f"Subprocess with proxy {proxy} failed: {str(sub_e)}")
                        continue
        
        # If we reached here, either:
        # 1. No proxies were available
        # 2. All proxies failed
        # Try direct connection with longer timeout if not already attempted
        logger.info("All proxies failed or none available, trying direct connection with longer timeout")
        
        # Try Python API without proxy (with longer timeout)
        try:
            ydl_opts = {
                'format': 'bestaudio',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': max_timeout,
                'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            }
            
            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                logger.info("Successfully extracted with direct connection and longer timeout")
                return {
                    'url': info['url'],
                    'title': info['title'],
                    'author': info['uploader'],
                    'thumbnail': info['thumbnail']
                }
        except Exception as e:
            logger.warning(f"Direct connection with longer timeout failed: {str(e)}")
            
            # Final attempt: Try subprocess without proxy
            try:
                cmd = f"yt-dlp --socket-timeout {max_timeout} {cookies_arg} -f bestaudio --dump-json {shlex.quote(url)}"
                logger.info(f"Running final subprocess without proxy: {cmd}")
                
                result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, timeout=max_timeout+5)
                if result.stdout:
                    info = json.loads(result.stdout)
                    logger.info("Successfully extracted with final subprocess without proxy")
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
