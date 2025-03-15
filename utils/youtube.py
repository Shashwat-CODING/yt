import logging
import os
import json
import random
import time
import requests
import re
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

def extract_audio_url(url):
    """Extract audio stream URL from YouTube Music using direct API requests"""
    try:
        # Define the path to the cookies file relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(current_dir, 'cookies.txt')
        
        # List of diverse user agents to avoid fingerprinting
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
        ]
        
        # Select a random user agent
        user_agent = random.choice(user_agents)
        
        # Extract video ID from various YouTube Music URL formats
        video_id = None
        
        # Direct YouTube Music watch URLs
        if 'music.youtube.com/watch' in url and 'v=' in url:
            video_id = re.search(r'v=([^&]+)', url).group(1)
        # YouTube Music playlist URLs
        elif 'music.youtube.com/playlist' in url and 'list=' in url:
            playlist_id = re.search(r'list=([^&]+)', url).group(1)
            logger.info(f"YouTube Music playlist detected: {playlist_id}")
            # For playlists, we'll need to first get the video IDs
            # This would require a different API call - for now we'll just extract from URL if possible
            if 'video_id' in url:
                video_id = re.search(r'video_id=([^&]+)', url).group(1)
            else:
                # We'd need separate logic to get first video from playlist
                # For now, fail gracefully
                raise Exception("For playlists, please provide a direct video URL from the playlist")
        # Handle YouTube's shortened URLs
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
        # Regular YouTube URLs
        elif 'youtube.com/watch' in url and 'v=' in url:
            video_id = re.search(r'v=([^&]+)', url).group(1)
        else:
            raise Exception("Could not extract video ID from URL")
        
        logger.info(f"Extracted video ID: {video_id}")
        
        # Read cookies from file if available
        cookies_dict = {}
        if os.path.exists(cookies_path):
            logger.info(f"Using cookies file: {cookies_path}")
            try:
                with open(cookies_path, 'r') as f:
                    cookie_content = f.read()
                    # Parse cookies content - this depends on the format of your cookies file
                    # This is a simplified version assuming Netscape cookie format
                    for line in cookie_content.split('\n'):
                        if line and not line.startswith('#'):
                            fields = line.strip().split('\t')
                            if len(fields) >= 7:
                                cookies_dict[fields[5]] = fields[6]
            except Exception as e:
                logger.warning(f"Error reading cookies file: {str(e)}")
        else:
            logger.warning(f"Cookies file not found at {cookies_path}")
        
        # Prepare headers for YouTube Music API request
        headers = {
            'User-Agent': user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,hi;q=0.7',
            'Content-Type': 'application/json',
            'Origin': 'https://music.youtube.com',
            'Referer': 'https://music.youtube.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-YouTube-Client-Name': '67',  # YouTube Music client ID
            'X-YouTube-Client-Version': '1.20250310.01.00',
            'X-Origin': 'https://music.youtube.com',
            'X-Goog-Visitor-Id': cookies_dict.get('VISITOR_INFO1_LIVE', ''),
        }
        
        # Add random delay before starting to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        # Prepare the request payload for YouTube Music API
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB_REMIX",
                    "clientVersion": "1.20250310.01.00",
                    "hl": "en",
                    "gl": "IN",  # Use India as region
                    "experimentIds": [],
                    "utcOffsetMinutes": 330,  # India timezone offset
                    "locationInfo": {
                        "locationPermissionAuthorizationStatus": "LOCATION_PERMISSION_AUTHORIZATION_STATUS_GRANTED"
                    },
                    "musicAppInfo": {
                        "musicActivityMasterSwitch": "MUSIC_ACTIVITY_MASTER_SWITCH_INDETERMINATE",
                        "musicLocationMasterSwitch": "MUSIC_LOCATION_MASTER_SWITCH_INDETERMINATE",
                        "pwaInstallabilityStatus": "PWA_INSTALLABILITY_STATUS_UNKNOWN"
                    }
                },
                "user": {
                    "lockedSafetyMode": False
                },
                "request": {
                    "useSsl": True,
                    "internalExperimentFlags": [],
                    "consistencyTokenJars": []
                }
            },
            "videoId": video_id,
            "playbackContext": {
                "contentPlaybackContext": {
                    "vis": 0,
                    "splay": False,
                    "autoCaptionsDefaultOn": False,
                    "autonavState": "STATE_NONE",
                    "html5Preference": "HTML5_PREF_WANTS",
                    "lactMilliseconds": "-1",
                    "referer": f"https://music.youtube.com/watch?v={video_id}"
                }
            },
            "racyCheckOk": True,
            "contentCheckOk": True
        }
        
        # Make the direct request to YouTube Music API
        response = requests.post(
            "https://music.youtube.com/youtubei/v1/player?prettyPrint=false",
            headers=headers,
            json=payload,
            cookies=cookies_dict
        )
        
        # Check if request was successful
        if response.status_code != 200:
            logger.error(f"API request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text[:200]}...")
            raise Exception(f"YouTube Music API request failed with status code: {response.status_code}")
        
        # Parse the response JSON
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error("Failed to parse API response as JSON")
            raise Exception("Could not parse YouTube Music API response")
        
        # Extract streaming URLs from the response
        streaming_data = data.get('streamingData', {})
        
        # Check for adaptive formats (usually higher quality)
        adaptive_formats = streaming_data.get('adaptiveFormats', [])
        
        # Filter for audio-only formats
        audio_formats = [
            fmt for fmt in adaptive_formats 
            if fmt.get('mimeType', '').startswith('audio/') and 'url' in fmt
        ]
        
        if not audio_formats:
            logger.warning("No audio-only formats found, checking all formats")
            # If no audio-only formats, check all formats for audio
            audio_formats = [
                fmt for fmt in adaptive_formats 
                if 'audio' in fmt.get('mimeType', '') and 'url' in fmt
            ]
        
        if audio_formats:
            # Sort by audio bitrate (highest first)
            audio_formats.sort(key=lambda x: int(x.get('bitrate', 0)), reverse=True)
            
            # Get the highest quality audio URL
            best_audio = audio_formats[0]
            audio_url = best_audio['url']
            
            bitrate = best_audio.get('bitrate', 0) // 1000  # Convert to kbps
            mime_type = best_audio.get('mimeType', '').split(';')[0]
            
            logger.info(f"Selected audio format: {mime_type} @ {bitrate}kbps")
            
            # Return the audio stream info
            return {
                'url': audio_url,
                'title': data.get('videoDetails', {}).get('title', 'Unknown Title'),
                'author': data.get('videoDetails', {}).get('author', 'Unknown Artist'),
                'thumbnail': data.get('videoDetails', {}).get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url') if data.get('videoDetails', {}).get('thumbnail', {}).get('thumbnails') else None,
                'duration': int(data.get('videoDetails', {}).get('lengthSeconds', 0))
            }
        else:
            # If no audio formats found in adaptive formats, try formats from streaming data
            formats = streaming_data.get('formats', [])
            
            if formats and 'url' in formats[0]:
                logger.info("Using fallback format")
                return {
                    'url': formats[0]['url'],
                    'title': data.get('videoDetails', {}).get('title', 'Unknown Title'),
                    'author': data.get('videoDetails', {}).get('author', 'Unknown Artist'),
                    'thumbnail': data.get('videoDetails', {}).get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url') if data.get('videoDetails', {}).get('thumbnail', {}).get('thumbnails') else None,
                    'duration': int(data.get('videoDetails', {}).get('lengthSeconds', 0))
                }
            else:
                raise Exception("No audio URLs found in the API response")
    
    except Exception as e:
        logger.error(f"Direct API extraction failed: {str(e)}")
        
        # Fallback to yt-dlp if available
        try:
            import yt_dlp
            logger.info("Falling back to yt-dlp extraction method")
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio',
                'geo_bypass': True,
                'geo_bypass_country': 'IN',
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android_music', 'web_music'],
                        'compat_opt': ['no-youtube-unavailable-videos']
                    }
                },
                'http_headers': {
                    'User-Agent': user_agent,
                    'X-YouTube-Client-Name': '67',  # YouTube Music web client
                    'X-YouTube-Client-Version': '1.20250310.01.00',
                    'Origin': 'https://music.youtube.com',
                    'Referer': 'https://music.youtube.com/'
                }
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Use video ID for most reliable extraction
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                
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
                
        except ImportError:
            logger.error("yt-dlp not available for fallback")
            raise Exception("Failed to extract audio URL from YouTube Music")
        except Exception as fallback_error:
            logger.error(f"Fallback extraction failed: {str(fallback_error)}")
            raise Exception("All extraction methods failed. This track may be region-restricted or require authentication.")
