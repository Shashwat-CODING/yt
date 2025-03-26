"""
YouTube Client module
Handles interaction with YouTube using the innertube package
"""

import os
import re
import time
import requests
from typing import List, Dict, Any, Optional, Tuple
import innertube
import pytube

class YouTubeClient:
    """
    Client for interacting with YouTube using innertube and pytube
    """
    
    def __init__(self):
        """Initialize YouTube client"""
        # Check if cookies.txt exists in the root directory
        cookies_file = "cookies.txt"
        cookies = None
        
        if os.path.exists(cookies_file):
            try:
                print(f"Using cookies from {cookies_file}")
                # Parse cookies file and convert to dictionary format
                cookies = self._parse_cookies_file(cookies_file)
            except Exception as e:
                print(f"Error parsing cookies file: {str(e)}")
        
        # Initialize innertube client with ANDROID client type for better compatibility
        # If cookies are available, pass them to the client
        if cookies:
            self.client = innertube.InnerTube("ANDROID", cookies=cookies)
        else:
            self.client = innertube.InnerTube("ANDROID")
            
    def _parse_cookies_file(self, cookies_file: str) -> dict:
        """
        Parse cookies.txt file (Netscape format) into a dictionary
        
        Args:
            cookies_file: Path to the cookies.txt file
            
        Returns:
            Dictionary of cookies
        """
        cookies = {}
        with open(cookies_file, 'r') as f:
            for line in f:
                # Skip comments and empty lines
                if line.startswith('#') or line.strip() == '':
                    continue
                
                try:
                    # Split the line into fields
                    fields = line.strip().split('\t')
                    if len(fields) >= 7:
                        domain, flag, path, secure, expiration, name, value = fields[:7]
                        # Only process .youtube.com cookies
                        if '.youtube.com' in domain:
                            cookies[name] = value
                except Exception as e:
                    print(f"Error parsing cookie line: {str(e)}")
                    
        return cookies
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos matching the query
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of dictionaries containing video information
        """
        try:
            # Use innertube to search YouTube
            search_results = self.client.search(query)
            
            videos = []
            count = 0
            
            # For ANDROID client, the structure is different
            # Let's handle multiple possible response structures
            
            # Try to find videos in richGridRenderer (common in ANDROID client)
            if 'contents' in search_results:
                if 'richGridRenderer' in search_results.get('contents', {}):
                    items = search_results['contents']['richGridRenderer'].get('contents', [])
                    for item in items:
                        if 'richItemRenderer' in item:
                            content = item['richItemRenderer'].get('content', {})
                            if 'videoRenderer' in content:
                                video_data = content['videoRenderer']
                                video = self._extract_video_info(video_data)
                                if video:
                                    videos.append(video)
                                    count += 1
                                    if count >= max_results:
                                        break
            
            # Try other possible structures if no videos found yet
            if not videos and 'contents' in search_results:
                # Try sectionListRenderer structure
                if 'sectionListRenderer' in search_results.get('contents', {}):
                    sections = search_results['contents']['sectionListRenderer'].get('contents', [])
                    for section in sections:
                        if 'itemSectionRenderer' in section:
                            items = section['itemSectionRenderer'].get('contents', [])
                            for item in items:
                                if 'videoRenderer' in item:
                                    video_data = item['videoRenderer']
                                    video = self._extract_video_info(video_data)
                                    if video:
                                        videos.append(video)
                                        count += 1
                                        if count >= max_results:
                                            break
            
            # If still no videos, use a more generic approach - search all nested dictionaries
            if not videos:
                print("Using fallback search method to find video renderers")
                video_renderers = self._find_all_video_renderers(search_results)
                for video_data in video_renderers[:max_results]:
                    video = self._extract_video_info(video_data)
                    if video:
                        videos.append(video)
            
            return videos
            
        except Exception as e:
            print(f"Error searching YouTube: {str(e)}")
            return []
    
    def _find_all_video_renderers(self, data, max_depth=10) -> List[Dict[str, Any]]:
        """
        Recursively search through the response to find all videoRenderer objects
        
        Args:
            data: Dictionary or list to search through
            max_depth: Maximum recursion depth
            
        Returns:
            List of videoRenderer dictionaries
        """
        results = []
        
        if max_depth <= 0:
            return results
            
        if isinstance(data, dict):
            # If this is a videoRenderer, add it to results
            if 'videoId' in data and ('title' in data or 'runs' in data.get('title', {})):
                results.append(data)
                
            # Otherwise, search through all values
            for value in data.values():
                results.extend(self._find_all_video_renderers(value, max_depth - 1))
                
        elif isinstance(data, list):
            # Search through all items in the list
            for item in data:
                results.extend(self._find_all_video_renderers(item, max_depth - 1))
                
        return results
            
    def _extract_video_info(self, video_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract video information from video renderer data
        
        Args:
            video_data: Video renderer data
            
        Returns:
            Dictionary containing video information or None if extraction fails
        """
        try:
            # Extract video ID
            video_id = video_data.get('videoId', '')
            if not video_id:
                return None
                
            # Extract title
            title = 'Unknown Title'
            if 'title' in video_data:
                if 'runs' in video_data['title']:
                    title = video_data['title']['runs'][0].get('text', 'Unknown Title')
                elif 'simpleText' in video_data['title']:
                    title = video_data['title']['simpleText']
            
            # Extract channel name
            channel = 'Unknown Channel'
            if 'ownerText' in video_data and 'runs' in video_data['ownerText']:
                channel = video_data['ownerText']['runs'][0].get('text', 'Unknown Channel')
            elif 'longBylineText' in video_data and 'runs' in video_data['longBylineText']:
                channel = video_data['longBylineText']['runs'][0].get('text', 'Unknown Channel')
            
            # Extract duration
            duration_text = 'Unknown'
            if 'lengthText' in video_data:
                if 'simpleText' in video_data['lengthText']:
                    duration_text = video_data['lengthText']['simpleText']
                elif 'runs' in video_data['lengthText']:
                    duration_text = video_data['lengthText']['runs'][0].get('text', 'Unknown')
            
            # Extract view count
            view_count = 'Unknown'
            if 'viewCountText' in video_data:
                if 'simpleText' in video_data['viewCountText']:
                    view_count = video_data['viewCountText']['simpleText']
                elif 'runs' in video_data['viewCountText']:
                    views_text = ' '.join([run.get('text', '') for run in video_data['viewCountText']['runs']])
                    if views_text:
                        view_count = views_text
            
            # Extract thumbnail
            thumbnail = ''
            if 'thumbnail' in video_data and 'thumbnails' in video_data['thumbnail']:
                thumbnails = video_data['thumbnail']['thumbnails']
                if thumbnails:
                    thumbnail = thumbnails[-1].get('url', '')
            
            # Add video information to the results
            return {
                'id': video_id,
                'title': title,
                'channel': channel,
                'duration': duration_text,
                'views': view_count,
                'thumbnail': thumbnail,
                'url': f"https://www.youtube.com/watch?v={video_id}"
            }
            
        except Exception as e:
            print(f"Error extracting video info: {str(e)}")
            return None
    
    def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dictionary containing video information or None if an error occurs
        """
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Create a PyTube YouTube instance
            # If cookies.txt exists, we'll need to manually set up cookies for PyTube
            cookies_file = "cookies.txt"
            if os.path.exists(cookies_file):
                print(f"Using cookies from {cookies_file} for PyTube")
                youtube = self._create_pytube_with_cookies(url, cookies_file)
            else:
                youtube = pytube.YouTube(url)
            
            return {
                'id': video_id,
                'title': youtube.title,
                'channel': youtube.author,
                'duration': self._format_duration(youtube.length),
                'views': youtube.views,
                'thumbnail': youtube.thumbnail_url,
                'url': url
            }
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return None
            
    def _create_pytube_with_cookies(self, url: str, cookies_file: str) -> pytube.YouTube:
        """
        Create a PyTube YouTube instance with cookies loaded from cookies.txt file
        
        Args:
            url: YouTube video URL
            cookies_file: Path to cookies.txt file
            
        Returns:
            PyTube YouTube instance with cookies
        """
        # Create YouTube instance
        yt = pytube.YouTube(url)
        
        # Parse cookies file
        cookie_dict = self._parse_cookies_file(cookies_file)
        
        # Convert dictionary to cookie string format for requests
        cookie_str = '; '.join([f'{name}={value}' for name, value in cookie_dict.items()])
        
        # Set up a session with cookies for PyTube to use
        if cookie_str:
            try:
                yt.bypass_age_gate = True
                if hasattr(yt, 'use_oauth'):
                    yt.use_oauth = False
                session = requests.Session()
                session.cookies.update({name: value for name, value in cookie_dict.items()})
                yt._http = session
                
                # Also add cookies to the header
                if hasattr(yt, 'headers'):
                    yt.headers['Cookie'] = cookie_str
            except Exception as e:
                print(f"Error setting up cookies for PyTube: {str(e)}")
                
        return yt
    
    def get_audio_stream(self, video_id: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Get the audio stream URL for a YouTube video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Tuple containing (stream_url, video_info) or (None, None) if an error occurs
        """
        try:
            # Get player data using InnerTube
            # If cookies.txt exists, use it when making the request
            cookies_file = "cookies.txt"
            if os.path.exists(cookies_file):
                print(f"Using cookies from {cookies_file} for InnerTube API")
                cookies = self._parse_cookies_file(cookies_file)
                # Try to add cookies to the client's session if possible
                if hasattr(self.client, '_session') and hasattr(self.client._session, 'cookies'):
                    self.client._session.cookies.update(cookies)
                
            data = self.client.player(video_id)
            
            # Extract video details
            video_details = data.get('videoDetails', {})
            title = video_details.get('title', 'Unknown Title')
            channel = video_details.get('author', 'Unknown Channel')
            length_seconds = int(video_details.get('lengthSeconds', 0))
            view_count = video_details.get('viewCount', 'Unknown')
            thumbnail_url = video_details.get('thumbnail', {}).get('thumbnails', [{}])[-1].get('url', '')
            
            # Create video info
            video_info = {
                'id': video_id,
                'title': title,
                'channel': channel,
                'duration': self._format_duration(length_seconds),
                'views': view_count,
                'thumbnail': thumbnail_url,
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'content_type': 'audio/mp4'  # Default content type
            }
            
            # Extract audio stream URL from streaming data
            formats = data.get('streamingData', {}).get('adaptiveFormats', [])
            audio_formats = [f for f in formats if f.get('mimeType', '').startswith('audio/')]
            
            if not audio_formats:
                print("No audio formats found for this video")
                return None, None
            
            # Sort by bitrate (higher is better)
            audio_formats.sort(key=lambda x: int(x.get('bitrate', 0)), reverse=True)
            best_audio = audio_formats[0]
            
            # Get direct streaming URL 
            audio_url = best_audio.get('url')
            
            if not audio_url:
                print("No direct URL available, may need to use cipher")
                if os.path.exists(cookies_file):
                    print("Attempting to get URL using PyTube with cookies...")
                    # Try to get the URL using PyTube with cookies
                    try:
                        url = f"https://www.youtube.com/watch?v={video_id}"
                        yt = self._create_pytube_with_cookies(url, cookies_file)
                        audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
                        if audio_streams:
                            best_stream = audio_streams.first()
                            # Get the direct URL
                            audio_url = best_stream.url
                            # Update content type if needed
                            if '.webm' in audio_url.lower():
                                video_info['content_type'] = 'audio/webm'
                            # If successful, return the URL
                            if audio_url:
                                return audio_url, video_info
                    except Exception as e:
                        print(f"Error getting URL from PyTube: {str(e)}")
                
                return None, None
                
            # Set the correct content type
            mime_type = best_audio.get('mimeType', 'audio/mp4')
            if 'audio/webm' in mime_type:
                video_info['content_type'] = 'audio/webm'
            
            # Add additional stream info
            video_info['bitrate'] = best_audio.get('bitrate', 0)
            video_info['mime_type'] = mime_type
            
            # Return the direct streaming URL and video info
            return audio_url, video_info
            
        except Exception as e:
            print(f"Error getting audio stream: {str(e)}")
            return None, None
    
    def _format_duration(self, seconds: int) -> str:
        """
        Format duration in seconds to MM:SS format
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
