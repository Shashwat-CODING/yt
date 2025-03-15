import logging
import os
import json
import yt_dlp
import webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

class HeadlessFlow(InstalledAppFlow):
    """Override InstalledAppFlow to support headless environments"""
    def run_local_server(self, **kwargs):
        self.redirect_uri = kwargs.get('redirect_uri', 'urn:ietf:wg:oauth:2.0:oob')
        auth_url, _ = self.authorization_url(**kwargs)
        print(f"\n\nPlease visit this URL to authorize this application: {auth_url}\n")
        print("After authorization, copy the code from the browser and paste it below.\n")
        code = input("Enter the authorization code: ")
        return self.fetch_token(code=code)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video using yt-dlp"""
    try:
        # Define paths relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        client_secrets_file = os.path.join(current_dir, 'client_secrets.json')
        token_file = os.path.join(current_dir, 'youtube_token.json')
        
        # Verify client_secrets.json exists
        if not os.path.exists(client_secrets_file):
            logger.error("client_secrets.json not found")
            raise FileNotFoundError(f"client_secrets.json is required for OAuth authentication. Expected at {client_secrets_file}")
        
        # Try to use direct API key approach first (doesn't require browser auth)
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'geo_bypass_country': 'IN',  # Set geo-location to India
                'geo_bypass': True,
            }
            
            # Attempt extraction without authentication first
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'url': info['url'],
                    'title': info['title'],
                    'author': info['uploader'],
                    'thumbnail': info['thumbnail']
                }
                
        except Exception as e:
            logger.warning(f"Initial extraction attempt failed: {str(e)}. Trying with OAuth...")
            
            # Fall back to manual OAuth process for server environments
            # Fall back to cookies if available
            cookies_path = os.path.join(current_dir, 'cookies.txt')
            if os.path.exists(cookies_path):
                logger.info(f"Found cookies file, using as fallback: {cookies_path}")
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'geo_bypass_country': 'IN',
                    'geo_bypass': True,
                    'cookiefile': cookies_path,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return {
                        'url': info['url'],
                        'title': info['title'],
                        'author': info['uploader'],
                        'thumbnail': info['thumbnail']
                    }
            else:
                raise Exception("No authentication method available. Both OAuth and cookies failed.")
                
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
