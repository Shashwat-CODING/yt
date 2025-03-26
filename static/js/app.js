// YouTube Audio Player Web App

// DOM Elements
const searchInput = document.getElementById('search-input');
const searchButton = document.getElementById('search-button');
const searchResults = document.getElementById('search-results');
const audioPlayer = document.getElementById('audio-player');
const currentTrack = document.getElementById('current-track');
const trackInfo = currentTrack.querySelector('.track-info');
const trackEmpty = currentTrack.querySelector('.track-empty');
const trackThumbnail = document.getElementById('track-thumbnail');
const trackTitle = document.getElementById('track-title');
const trackChannel = document.getElementById('track-channel');
const trackDuration = document.getElementById('track-duration');
const playlistName = document.getElementById('playlist-name');
const createPlaylistButton = document.getElementById('create-playlist-button');
const playlistsList = document.getElementById('playlists');
const playlistTracks = document.getElementById('playlist-tracks');
const currentPlaylistName = document.getElementById('current-playlist-name');
const playlistTracksList = document.getElementById('playlist-tracks-list');
const playlistSelectionModal = document.getElementById('playlist-selection-modal');
const playlistSelectionList = document.getElementById('playlist-selection-list');
const closeModal = document.querySelector('.close-modal');

// Templates
const searchResultTemplate = document.getElementById('search-result-template');
const playlistItemTemplate = document.getElementById('playlist-item-template');
const playlistTrackTemplate = document.getElementById('playlist-track-template');

// State
let searchResultsData = [];
let playlists = [];
let currentPlaylist = null;
let playlistTracksData = [];
let selectedTrackForPlaylist = null;

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Load playlists when the page loads
    loadPlaylists();
    
    // Search functionality
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    searchButton.addEventListener('click', performSearch);
    
    // Audio player events
    audioPlayer.addEventListener('ended', () => {
        // Could implement auto-play next track in playlist here
        showNotification('Playback ended', 'success');
    });
    
    // Create playlist
    createPlaylistButton.addEventListener('click', createPlaylist);
    
    // Close modal
    closeModal.addEventListener('click', () => {
        playlistSelectionModal.style.display = 'none';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === playlistSelectionModal) {
            playlistSelectionModal.style.display = 'none';
        }
    });
});

// Functions
async function performSearch() {
    const query = searchInput.value.trim();
    
    if (!query) {
        showNotification('Please enter a search query', 'error');
        return;
    }
    
    try {
        searchResults.innerHTML = '<div class="loading">Searching...</div>';
        
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            searchResultsData = data.results;
            displaySearchResults(searchResultsData);
        } else {
            showNotification(data.error || 'Search failed', 'error');
            searchResults.innerHTML = '<div class="error">Search failed</div>';
        }
    } catch (error) {
        console.error('Search error:', error);
        showNotification('An error occurred while searching', 'error');
        searchResults.innerHTML = '<div class="error">An error occurred</div>';
    }
}

function displaySearchResults(results) {
    searchResults.innerHTML = '';
    
    if (results.length === 0) {
        searchResults.innerHTML = '<div class="no-results">No results found</div>';
        return;
    }
    
    results.forEach((result, index) => {
        const resultItem = searchResultTemplate.content.cloneNode(true);
        
        // Set data
        const thumbnail = resultItem.querySelector('.result-thumbnail img');
        const title = resultItem.querySelector('.result-title');
        const channel = resultItem.querySelector('.result-channel');
        const duration = resultItem.querySelector('.result-duration');
        const playButton = resultItem.querySelector('.play-button');
        const addToPlaylistButton = resultItem.querySelector('.add-to-playlist-button');
        
        thumbnail.src = result.thumbnail || 'https://via.placeholder.com/120x70';
        thumbnail.alt = result.title;
        title.textContent = result.title;
        channel.textContent = result.channel;
        duration.textContent = result.duration;
        
        // Add event listeners
        playButton.addEventListener('click', () => {
            playTrack(result);
        });
        
        addToPlaylistButton.addEventListener('click', () => {
            selectedTrackForPlaylist = result;
            showPlaylistSelectionModal();
        });
        
        searchResults.appendChild(resultItem);
    });
}

async function playTrack(track) {
    try {
        showNotification(`Loading: ${track.title}`, 'success');
        
        const response = await fetch('/api/play', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ video_id: track.id }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Update UI
            updateNowPlaying(data.track_info);
            
            // Use the direct streaming URL from YouTube
            audioPlayer.src = data.track_info.streaming_url;
            audioPlayer.play().catch(e => {
                console.error('Error playing audio:', e);
                showNotification('Error playing audio. Please try again.', 'error');
            });
        } else {
            showNotification(data.error || 'Failed to play track', 'error');
        }
    } catch (error) {
        console.error('Play error:', error);
        showNotification('An error occurred while playing track', 'error');
    }
}

function updateNowPlaying(track) {
    if (!track) {
        trackEmpty.style.display = 'flex';
        trackInfo.style.display = 'none';
        return;
    }
    
    trackEmpty.style.display = 'none';
    trackInfo.style.display = 'flex';
    
    trackThumbnail.src = track.thumbnail || 'https://via.placeholder.com/160x90';
    trackTitle.textContent = track.title;
    trackChannel.textContent = track.channel;
    trackDuration.textContent = track.duration;
}

async function loadPlaylists() {
    try {
        const response = await fetch('/api/playlists');
        const data = await response.json();
        
        if (response.ok) {
            playlists = data.playlists;
            displayPlaylists();
        } else {
            showNotification(data.error || 'Failed to load playlists', 'error');
        }
    } catch (error) {
        console.error('Load playlists error:', error);
        showNotification('An error occurred while loading playlists', 'error');
    }
}

function displayPlaylists() {
    playlistsList.innerHTML = '';
    
    if (playlists.length === 0) {
        playlistsList.innerHTML = '<div class="no-playlists">No playlists found</div>';
        return;
    }
    
    playlists.forEach(playlist => {
        const playlistItem = playlistItemTemplate.content.cloneNode(true);
        
        // Set data
        const playlistNameElement = playlistItem.querySelector('.playlist-name');
        const loadButton = playlistItem.querySelector('.load-playlist-button');
        const deleteButton = playlistItem.querySelector('.delete-playlist-button');
        
        playlistNameElement.textContent = playlist;
        
        // Add event listeners
        loadButton.addEventListener('click', () => {
            loadPlaylistTracks(playlist);
        });
        
        deleteButton.addEventListener('click', () => {
            deletePlaylist(playlist);
        });
        
        playlistsList.appendChild(playlistItem);
    });
}

async function createPlaylist() {
    const name = playlistName.value.trim();
    
    if (!name) {
        showNotification('Please enter a playlist name', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/playlists', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message || 'Playlist created', 'success');
            playlistName.value = '';
            loadPlaylists();
        } else {
            showNotification(data.error || 'Failed to create playlist', 'error');
        }
    } catch (error) {
        console.error('Create playlist error:', error);
        showNotification('An error occurred while creating playlist', 'error');
    }
}

async function deletePlaylist(name) {
    if (!confirm(`Are you sure you want to delete playlist "${name}"?`)) {
        return;
    }
    
    try {
        // This would need a corresponding API endpoint
        const response = await fetch(`/api/playlists/${name}`, {
            method: 'DELETE',
        });
        
        if (response.ok) {
            showNotification(`Playlist "${name}" deleted`, 'success');
            
            // If the current playlist is deleted, hide playlist tracks
            if (currentPlaylist === name) {
                currentPlaylist = null;
                playlistTracks.style.display = 'none';
            }
            
            loadPlaylists();
        } else {
            const data = await response.json();
            showNotification(data.error || 'Failed to delete playlist', 'error');
        }
    } catch (error) {
        console.error('Delete playlist error:', error);
        showNotification('An error occurred while deleting playlist', 'error');
    }
}

async function loadPlaylistTracks(name) {
    try {
        const response = await fetch(`/api/playlists/${name}`);
        const data = await response.json();
        
        if (response.ok) {
            currentPlaylist = name;
            playlistTracksData = data.tracks;
            
            // Update UI
            currentPlaylistName.textContent = name;
            displayPlaylistTracks();
            playlistTracks.style.display = 'block';
        } else {
            showNotification(data.error || 'Failed to load playlist tracks', 'error');
        }
    } catch (error) {
        console.error('Load playlist tracks error:', error);
        showNotification('An error occurred while loading playlist tracks', 'error');
    }
}

function displayPlaylistTracks() {
    playlistTracksList.innerHTML = '';
    
    if (playlistTracksData.length === 0) {
        playlistTracksList.innerHTML = '<div class="no-tracks">This playlist is empty</div>';
        return;
    }
    
    playlistTracksData.forEach(track => {
        const trackItem = playlistTrackTemplate.content.cloneNode(true);
        
        // Set data
        const trackTitle = trackItem.querySelector('.track-title');
        const trackChannel = trackItem.querySelector('.track-channel');
        const playButton = trackItem.querySelector('.play-track-button');
        const removeButton = trackItem.querySelector('.remove-track-button');
        
        trackTitle.textContent = track.title;
        trackChannel.textContent = track.channel;
        
        // Add event listeners
        playButton.addEventListener('click', () => {
            playTrack(track);
        });
        
        removeButton.addEventListener('click', () => {
            removeTrackFromPlaylist(track.id);
        });
        
        playlistTracksList.appendChild(trackItem);
    });
}

async function removeTrackFromPlaylist(trackId) {
    if (!currentPlaylist) return;
    
    try {
        const response = await fetch(`/api/playlists/${currentPlaylist}/remove`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ track_id: trackId }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message || 'Track removed from playlist', 'success');
            loadPlaylistTracks(currentPlaylist);
        } else {
            showNotification(data.error || 'Failed to remove track from playlist', 'error');
        }
    } catch (error) {
        console.error('Remove track error:', error);
        showNotification('An error occurred while removing track from playlist', 'error');
    }
}

function showPlaylistSelectionModal() {
    // Clear previous content
    playlistSelectionList.innerHTML = '';
    
    if (playlists.length === 0) {
        playlistSelectionList.innerHTML = '<div class="no-playlists">No playlists found. Create a playlist first.</div>';
    } else {
        playlists.forEach(playlist => {
            const div = document.createElement('div');
            div.className = 'playlist-selection-item';
            div.textContent = playlist;
            
            div.addEventListener('click', () => {
                addSelectedTrackToPlaylist(playlist);
                playlistSelectionModal.style.display = 'none';
            });
            
            playlistSelectionList.appendChild(div);
        });
    }
    
    // Show the modal
    playlistSelectionModal.style.display = 'flex';
}

async function addSelectedTrackToPlaylist(playlistName) {
    if (!selectedTrackForPlaylist) return;
    
    try {
        const response = await fetch(`/api/playlists/${playlistName}/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ track: selectedTrackForPlaylist }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification(data.message || `Track added to ${playlistName}`, 'success');
            
            // If the current playlist is the one we added to, refresh it
            if (currentPlaylist === playlistName) {
                loadPlaylistTracks(playlistName);
            }
        } else {
            showNotification(data.error || 'Failed to add track to playlist', 'error');
        }
    } catch (error) {
        console.error('Add to playlist error:', error);
        showNotification('An error occurred while adding track to playlist', 'error');
    }
    
    // Reset selected track
    selectedTrackForPlaylist = null;
}

// Utility functions
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Add to document
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Hide and remove after delay
    setTimeout(() => {
        notification.classList.remove('show');
        
        // Remove from DOM after transition
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}