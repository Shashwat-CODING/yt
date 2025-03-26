"""
Playlist Manager module
Handles creating and managing playlists
"""

import os
import json
from typing import List, Dict, Any, Optional

class PlaylistManager:
    """
    Manages playlists for the YouTube Audio Player
    """
    
    def __init__(self, playlists_dir: str = "playlists"):
        """
        Initialize playlist manager
        
        Args:
            playlists_dir: Directory to store playlist files
        """
        self.playlists_dir = playlists_dir
        self.current_playlist = None
        self.current_index = -1
        
        # Create playlists directory if it doesn't exist
        os.makedirs(self.playlists_dir, exist_ok=True)
    
    def get_playlists(self) -> List[str]:
        """
        Get a list of available playlists
        
        Returns:
            List of playlist names
        """
        try:
            playlists = []
            for filename in os.listdir(self.playlists_dir):
                if filename.endswith('.json'):
                    playlists.append(filename[:-5])  # Remove .json extension
            return playlists
        except Exception as e:
            print(f"Error getting playlists: {str(e)}")
            return []
    
    def create_playlist(self, name: str) -> bool:
        """
        Create a new empty playlist
        
        Args:
            name: Name of the playlist
            
        Returns:
            True if playlist was created successfully, False otherwise
        """
        try:
            # Sanitize playlist name
            safe_name = ''.join(c for c in name if c.isalnum() or c in ' _-')
            
            # Create playlist file
            playlist_path = os.path.join(self.playlists_dir, f"{safe_name}.json")
            
            # Check if playlist already exists
            if os.path.exists(playlist_path):
                print(f"Playlist '{name}' already exists")
                return False
            
            # Create empty playlist
            with open(playlist_path, 'w') as f:
                json.dump([], f)
            
            return True
        
        except Exception as e:
            print(f"Error creating playlist: {str(e)}")
            return False
    
    def load_playlist(self, name: str) -> List[Dict[str, Any]]:
        """
        Load a playlist from file
        
        Args:
            name: Name of the playlist
            
        Returns:
            List of track dictionaries
        """
        try:
            playlist_path = os.path.join(self.playlists_dir, f"{name}.json")
            
            if not os.path.exists(playlist_path):
                print(f"Playlist '{name}' not found")
                return []
            
            with open(playlist_path, 'r') as f:
                playlist = json.load(f)
            
            self.current_playlist = name
            self.current_index = 0 if playlist else -1
            
            return playlist
        
        except Exception as e:
            print(f"Error loading playlist: {str(e)}")
            return []
    
    def save_playlist(self, name: str, tracks: List[Dict[str, Any]]) -> bool:
        """
        Save a playlist to file
        
        Args:
            name: Name of the playlist
            tracks: List of track dictionaries
            
        Returns:
            True if playlist was saved successfully, False otherwise
        """
        try:
            # Sanitize playlist name
            safe_name = ''.join(c for c in name if c.isalnum() or c in ' _-')
            
            playlist_path = os.path.join(self.playlists_dir, f"{safe_name}.json")
            
            with open(playlist_path, 'w') as f:
                json.dump(tracks, f, indent=2)
            
            return True
        
        except Exception as e:
            print(f"Error saving playlist: {str(e)}")
            return False
    
    def delete_playlist(self, name: str) -> bool:
        """
        Delete a playlist
        
        Args:
            name: Name of the playlist
            
        Returns:
            True if playlist was deleted successfully, False otherwise
        """
        try:
            playlist_path = os.path.join(self.playlists_dir, f"{name}.json")
            
            if not os.path.exists(playlist_path):
                print(f"Playlist '{name}' not found")
                return False
            
            os.remove(playlist_path)
            
            if self.current_playlist == name:
                self.current_playlist = None
                self.current_index = -1
            
            return True
        
        except Exception as e:
            print(f"Error deleting playlist: {str(e)}")
            return False
    
    def add_to_playlist(self, name: str, track: Dict[str, Any]) -> bool:
        """
        Add a track to a playlist
        
        Args:
            name: Name of the playlist
            track: Track dictionary
            
        Returns:
            True if track was added successfully, False otherwise
        """
        try:
            playlist = self.load_playlist(name)
            
            # Check if track is already in playlist
            for existing_track in playlist:
                if existing_track.get('id') == track.get('id'):
                    print(f"Track already exists in playlist '{name}'")
                    return False
            
            # Add track to playlist
            playlist.append(track)
            
            # Save updated playlist
            return self.save_playlist(name, playlist)
        
        except Exception as e:
            print(f"Error adding track to playlist: {str(e)}")
            return False
    
    def remove_from_playlist(self, name: str, track_id: str) -> bool:
        """
        Remove a track from a playlist
        
        Args:
            name: Name of the playlist
            track_id: ID of the track to remove
            
        Returns:
            True if track was removed successfully, False otherwise
        """
        try:
            playlist = self.load_playlist(name)
            
            # Find track index
            for i, track in enumerate(playlist):
                if track.get('id') == track_id:
                    # Remove track
                    del playlist[i]
                    
                    # Update current index if necessary
                    if self.current_playlist == name and self.current_index >= i:
                        self.current_index = max(0, self.current_index - 1)
                    
                    # Save updated playlist
                    return self.save_playlist(name, playlist)
            
            print(f"Track not found in playlist '{name}'")
            return False
        
        except Exception as e:
            print(f"Error removing track from playlist: {str(e)}")
            return False
    
    def get_current_playlist(self) -> Optional[str]:
        """
        Get the name of the current playlist
        
        Returns:
            Name of the current playlist or None if no playlist is loaded
        """
        return self.current_playlist
    
    def get_current_track(self) -> Optional[Dict[str, Any]]:
        """
        Get the current track in the playlist
        
        Returns:
            Dictionary containing track information or None if no track is current
        """
        if not self.current_playlist or self.current_index < 0:
            return None
        
        playlist = self.load_playlist(self.current_playlist)
        
        if not playlist or self.current_index >= len(playlist):
            return None
        
        return playlist[self.current_index]
    
    def next_track(self) -> Optional[Dict[str, Any]]:
        """
        Move to the next track in the playlist
        
        Returns:
            Dictionary containing track information or None if no next track
        """
        if not self.current_playlist:
            return None
        
        playlist = self.load_playlist(self.current_playlist)
        
        if not playlist:
            return None
        
        # Increment index and wrap around if necessary
        self.current_index = (self.current_index + 1) % len(playlist)
        
        return playlist[self.current_index]
    
    def previous_track(self) -> Optional[Dict[str, Any]]:
        """
        Move to the previous track in the playlist
        
        Returns:
            Dictionary containing track information or None if no previous track
        """
        if not self.current_playlist:
            return None
        
        playlist = self.load_playlist(self.current_playlist)
        
        if not playlist:
            return None
        
        # Decrement index and wrap around if necessary
        self.current_index = (self.current_index - 1) % len(playlist)
        
        return playlist[self.current_index]
