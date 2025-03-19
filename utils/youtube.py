import logging
import os
import json
import yt_dlp
import requests
import random
import time

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video using yt-dlp with enhanced geo-bypass techniques"""
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
        
        # Get proxies from the dynamic JSON
        try:
            response = requests.get("https://raw.githubusercontent.com/Shashwat-CODING/yt/refs/heads/main/wpr.json")
            if response.status_code == 200:
                proxy_data = response.json()
                proxies = proxy_data.get('proxies', [])
                logger.info(f"Fetched {len(proxies)} proxies")
                # Shuffle proxies for better distribution
                random.shuffle(proxies)
            else:
                proxies = []
                logger.warning("Failed to fetch proxies, proceeding without proxies")
        except Exception as e:
            proxies = []
            logger.warning(f"Error fetching proxies: {str(e)}")
        
        # Common headers that can help bypass geo-restrictions
        headers = {
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.youtube.com/',
            'X-Forwarded-For': '103.48.198.141',  # Indian IP address
        }
        
        # List of countries to try (India first, then others that might work)
        countries = ['IN', 'US', 'GB', 'CA', 'JP', 'SG']
        
        # Try each proxy with different country settings
        last_error = None
        for proxy in proxies:
            for country in countries:
                try:
                    logger.info(f"Trying proxy {proxy} with country {country}")
                    
                    # Configure yt-dlp options with comprehensive geo-bypass settings
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': False,
                        'user_agent': headers['User-Agent'],
                        'client_secrets': client_secrets_file,
                        'geo_verification_proxy': proxy,
                        'geo_bypass_country': country,
                        'geo_bypass': True,
                        'geo_bypass_ip_block': '103.48.198.0/24',  # Indian IP block
                        'http_headers': headers,
                        'socket_timeout': 15,
                        'retries': 3,
                    }
                    
                    # Fallback to cookies if available
                    cookies_path = os.path.join(current_dir, 'cookies.txt')
                    if os.path.exists(cookies_path):
                        logger.info(f"Found cookies file, using as fallback: {cookies_path}")
                        ydl_opts['cookiefile'] = cookies_path
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        logger.info(f"Successfully extracted with proxy {proxy} and country {country}")
                        return {
                            'url': info['url'],
                            'title': info['title'],
                            'author': info['uploader'],
                            'thumbnail': info['thumbnail']
                        }
                except Exception as e:
                    last_error = e
                    logger.warning(f"Failed with proxy {proxy} and country {country}: {str(e)}")
                    # Small delay to avoid rapid-fire requests
                    time.sleep(0.5)
                    continue
        
        # If all proxies fail, try without proxy but with forced geo-bypass settings
        logger.info("All proxies failed or none available, trying without proxy but with forced geo-bypass")
        for country in countries:
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'user_agent': headers['User-Agent'],
                    'client_secrets': client_secrets_file,
                    'geo_verification_proxy': '',  # Empty string for auto-detect
                    'geo_bypass_country': country,
                    'geo_bypass': True,
                    'geo_bypass_ip_block': '103.48.198.0/24',  # Indian IP block
                    'http_headers': headers,
                    'socket_timeout': 15,
                    'retries': 3,
                }
                
                # Fallback to cookies if available
                cookies_path = os.path.join(current_dir, 'cookies.txt')
                if os.path.exists(cookies_path):
                    ydl_opts['cookiefile'] = cookies_path
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"Successfully extracted without proxy using country {country}")
                    return {
                        'url': info['url'],
                        'title': info['title'],
                        'author': info['uploader'],
                        'thumbnail': info['thumbnail']
                    }
            except Exception as e:
                logger.warning(f"Failed without proxy using country {country}: {str(e)}")
                continue
        
        # If all attempts fail, raise the last error
        logger.error(f"All extraction attempts failed: {str(last_error)}")
        raise Exception(f"Failed to extract audio: {str(last_error)}")
            
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
