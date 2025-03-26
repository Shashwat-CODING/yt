#!/usr/bin/env python3

"""
YouTube Audio Player Web App
A web application that allows users to search, extract, and play audio from YouTube videos.
"""

import os
import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from modules.youtube_client import YouTubeClient
from modules.audio_player import AudioPlayer
from modules.playlist_manager import PlaylistManager

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Initialize components
youtube_client = YouTubeClient()
audio_player = AudioPlayer()
playlist_manager = PlaylistManager()

# Store current track info
current_track = None

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    """Search YouTube for videos"""
    data = request.json
    query = data.get('query', '')
    max_results = data.get('max_results', 10)
    
    if not query:
        return jsonify({'error': 'No search query provided'}), 400
    
    # Search YouTube
    results = youtube_client.search(query, max_results)
    
    return jsonify({'results': results})

@app.route('/api/play', methods=['POST'])
def play():
    """Play a YouTube video's audio"""
    global current_track
    
    data = request.json
    video_id = data.get('video_id', '')
    
    if not video_id:
        return jsonify({'error': 'No video ID provided'}), 400
    
    # Get direct streaming URL from YouTube
    streaming_url, video_info = youtube_client.get_audio_stream(video_id)
    
    if not streaming_url or not video_info:
        return jsonify({'error': 'Failed to get audio stream'}), 500
    
    # Store current track info
    current_track = video_info
    
    # Include the direct streaming URL in the response
    video_info['streaming_url'] = streaming_url
    
    return jsonify({
        'track_info': video_info
    })

@app.route('/api/playlists', methods=['GET'])
def get_playlists():
    """Get all available playlists"""
    playlists = playlist_manager.get_playlists()
    return jsonify({'playlists': playlists})

@app.route('/api/playlists', methods=['POST'])
def create_playlist():
    """Create a new playlist"""
    data = request.json
    name = data.get('name', '')
    
    if not name:
        return jsonify({'error': 'No playlist name provided'}), 400
    
    success = playlist_manager.create_playlist(name)
    
    if not success:
        return jsonify({'error': f'Failed to create playlist {name}'}), 500
    
    return jsonify({'success': True, 'message': f'Playlist {name} created'})

@app.route('/api/playlists/<name>', methods=['GET', 'DELETE'])
def playlist_operations(name):
    """Operations on a specific playlist (GET or DELETE)"""
    if request.method == 'GET':
        tracks = playlist_manager.load_playlist(name)
        return jsonify({'tracks': tracks})
    elif request.method == 'DELETE':
        success = playlist_manager.delete_playlist(name)
        if success:
            return jsonify({'success': True, 'message': f'Playlist {name} deleted'})
        else:
            return jsonify({'error': f'Failed to delete playlist {name}'}), 500

@app.route('/api/playlists/<name>/add', methods=['POST'])
def add_to_playlist(name):
    """Add a track to a playlist"""
    data = request.json
    track = data.get('track', {})
    
    if not track:
        return jsonify({'error': 'No track provided'}), 400
    
    success = playlist_manager.add_to_playlist(name, track)
    
    if not success:
        return jsonify({'error': f'Failed to add track to playlist {name}'}), 500
    
    return jsonify({'success': True, 'message': f'Track added to playlist {name}'})

@app.route('/api/playlists/<name>/remove', methods=['POST'])
def remove_from_playlist(name):
    """Remove a track from a playlist"""
    data = request.json
    track_id = data.get('track_id', '')
    
    if not track_id:
        return jsonify({'error': 'No track ID provided'}), 400
    
    success = playlist_manager.remove_from_playlist(name, track_id)
    
    if not success:
        return jsonify({'error': f'Failed to remove track from playlist {name}'}), 500
    
    return jsonify({'success': True, 'message': f'Track removed from playlist {name}'})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current playback status"""
    global current_track
    
    if not current_track:
        return jsonify({'playing': False})
    
    return jsonify({
        'playing': True,
        'track': current_track
    })

if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)