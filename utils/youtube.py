import logging
import os
import json
import yt_dlp
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube video using yt-dlp with OAuth authentication"""
    try:
        # Define paths relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        client_secrets_file = os.path.join(current_dir, 'client_secrets.json')
        token_file = os.path.join(current_dir, 'youtube_token.json')
        
        # Verify client_secrets.json exists
        if not os.path.exists(client_secrets_file):
            logger.error("client_secrets.json not found")
            raise FileNotFoundError("client_secrets.json is required for OAuth authentication")
        
        # Get OAuth token
        credentials = None
        if os.path.exists(token_file):
            credentials = Credentials.from_authorized_user_info(
                json.load(open(token_file)), ['https://www.googleapis.com/auth/youtube.readonly']
            )
        
        # If credentials don't exist or are expired, run the OAuth flow
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secrets_file,
                    ['https://www.googleapis.com/auth/youtube.readonly']
                )
                credentials = flow.run_local_server(port=0)
            
            # Save the token
            with open(token_file, 'w') as token:
                token.write(credentials.to_json())
            logger.info(f"Saved OAuth token to {token_file}")
        
        # Configure yt-dlp options with OAuth
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'geo_bypass_country': 'IN',  # Set geo-location to India
            'geo_bypass': True,
        }
        
        # Add OAuth token to requests
        auth_header = f"Bearer {credentials.token}"
        ydl_opts['http_headers'] = {'Authorization': auth_header}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'url': info['url'],
                'title': info['title'],
                'author': info['uploader'],
                'thumbnail': info['thumbnail']
            }
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {str(e)}")
        raise Exception(f"Failed to extract audio: {str(e)}")
