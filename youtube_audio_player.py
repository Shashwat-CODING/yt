#!/usr/bin/env python3

"""
YouTube Audio Player
A terminal-based application that allows users to search, extract, and play audio from YouTube videos.
"""

import os
import sys
import signal
from modules.youtube_client import YouTubeClient
from modules.audio_player import AudioPlayer
from modules.playlist_manager import PlaylistManager
from modules.terminal_ui import TerminalUI

def signal_handler(sig, frame):
    """Handle keyboard interrupts gracefully"""
    print("\nExiting YouTube Audio Player...")
    # Ensure we clean up any resources before exiting
    if hasattr(signal_handler, 'audio_player') and signal_handler.audio_player:
        signal_handler.audio_player.stop()
    sys.exit(0)

def main():
    """Main entry point for the YouTube Audio Player"""
    # Register signal handler for CTRL+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize components
    youtube_client = YouTubeClient()
    audio_player = AudioPlayer()
    # Store reference to allow cleanup on exit
    signal_handler.audio_player = audio_player
    
    playlist_manager = PlaylistManager()
    terminal_ui = TerminalUI(youtube_client, audio_player, playlist_manager)
    
    # Start the application
    terminal_ui.run()

if __name__ == "__main__":
    main()
